#!/usr/bin/env python
"""
RTEVariable.py
"""
__version__ = "$Revision: 1.2 $"
__revision__ = "$Id: RTEVariable.py,v 1.2 2006/01/18 21:16:01 ratnik Exp $"

# DAR  Version 2.0
# Natalia Ratnikova  2003-04.
#
# Module  RTEVariable:
#                            - defines classes and corresponding  methods
#                              for various variable types
##############################################################

import os
import string

from Utils import convertPatternList, Lister, Bunch, DARInternalError, warning
from Utils import eliminatePathDuplicates

from FSO import createFSO

class RTEVariable(Lister):
    """A runtime environment variable."""
    def __init__(self,  name, value):
        self.varName = name
        self.varValue = value
        self.type = None
        self.fso = None
        self.fsoList = None
        self._IgnoreStatus = None
        self.preserveList = []
        self.excludeList = []
        self.alwaysKeepList = []
        self.setups = [] #   for setupEnv scripts

    def setValue(self,  value):
        """RTEVariable.setValue"""
        raise NotImplementedError, "setValue()"
    
    def arg(self):
        """Returns a Bunch object representing the preserveList, excludeList and alwaysKeepList attributes."""
        return Bunch(
            preserveList = self.preserveList, 
            excludeList = self.excludeList, 
            alwaysKeepList = self.alwaysKeepList
            )
    
    def getValue(self):
        """Returns varValue."""
        return self.varValue
    
    def copyContent(self,  dar,  method,  baseBom = {}):
        """RTEVariable.copyContent."""
        pass  # implemented in  PathToFile and PathToDir

    def ignore(self):
        """
        Boolean method returning whether or not this variable is to be ignored.
        """
        self._IgnoreStatus = 'yes'
        
    def ignored(self):
        """
        Returns true if this variable is to be ignored.
        """
        return self._IgnoreStatus == 'yes'

    def preservePattern (self,  patterns):
        """
        Sets the preserveList attribute by converting the pattern list given in patterns.
        """
        self.preserveList = convertPatternList(patterns)

    def excludePattern (self,  patterns):
        """
        Sets the excludeList attribute by converting the list given in patterns.
        """
        self.excludeList = convertPatternList(patterns)
        
    def alwaysKeepPattern (self,  patterns):
        """
        Sets alwaysKeepList by converting the list given in patterns.
        """
        self.alwaysKeepList = convertPatternList(patterns)
        
    def setEnv (self,  instDir,  stub,  shell):
        """
        Sets environment variables
        """
        # if not self.setups: return
        # always set up,  even if undefined value 
        value = ''
        for setup in self.setups:
            if value:
                value = value+":"+setup
            else:
                value = setup
        newValue = string.replace(value,  instDir,  stub)
        if shell == "csh":
            return "setenv %s \"%s\";\n" % (self.varName,  newValue)
        if shell == "sh":
            return "%s=\"%s\";\nexport %s;\n"% (self.varName,  newValue,  self.varName)
        # If still did not return:
        DARInternalError('in RTEVariable.setEnv: which shell ??')

class PathToFile(RTEVariable):
    """A runtime environment object representing a complete path to an individual file."""
    
    def __init__(self, name, value):
        RTEVariable.__init__(self, name, value)
        self.type = 'RTEVariable'
    
    def setValue(self,  value):
        """
        Sets value and filename for this object.
        """
        if os.isfile(value): # allow to overwrite  files only with existing files
            self.varValue = value
            self.filename = os.path.basename(value)
        else:
            raise IncorrectValue,  value+" in PathToFile.setValue()"

    def createFso(self, value):
        """
        Sets fso attribute by calling FSO.createFSO.
        """
        self.fso = createFSO(value,  self.arg())
        
    def copyContent (self,  dar,  method,  baseBom = {}):
        """
        Copies the contents of fso ??????.
        """
        if self.ignored():
            return

        rteDirectory = dar.getRteTop()+"/"+self.varName
        self.fso.copyContent (dar.getSharedTop(), rteDirectory,  dar.getBaseTop(),  baseBom,  method)
        self.setups = [rteDirectory+"/"+self.filename, ]


class SimpleValue(RTEVariable):
    """
    Represents a simple runtime environment variable.
    """

    def __init__(self, name, value):
        RTEVariable.__init__(self, name, value)
        self.type = 'RTEVariable'
        self.setups = [value, ]        

    def setValue(self,  value):
        """
        Sets varValue.
        """
        self.varValue = value
        self.setups = [value, ]        

    def testCommand(self,  value):
        """
        Executes a test command.
        """
        print "executing testCommand for ",  value


class PathToDir(RTEVariable):
    """
    Represents a runtime environment variable mirroring a complete directory
    """
    separator = ":"

    def __init__(self, name, value):
        value = eliminatePathDuplicates(value)
        RTEVariable.__init__(self, name, value)
        self.type = 'RTEVariable'

    def createFso(self):
        """
        Creates a list of FSO objects and appends them to fsoList.
        """
        self.fsoList = []
        for location in string.split(self.varValue, self.separator):
            # extra  bracket is important!
            self.fsoList.append ((location, createFSO(location,  self.arg()))) 
                    
    def setValue(self,  value):
        """
        Sets varValue.
        """
        # Any checks needed? 
        self.varValue = value
        self.createFso()
        
    def prependPath(self, locationList):
        """
        Prepends new FSO objects to the front of fsoLIst.
        """
        for location in locationList:
            newValue = location+self.separator+self.varValue
            self.setValue(newValue)
            # update fso:
            self.fsoList[:0] = [(location,  createFSO(location, self.arg()))]

    def postpendPath(self, locationList):
        """
        Postpends new FSO objects to the end of the list.
        """
        for location in locationList:
            newValue = self.varValue+self.separator+location
            self.setValue(newValue)
            # update fso:
            self.fsoList.append ((location,  createFSO(location, self.arg())))

    def removeDuplicates(self):
        """
        PathToDir.removeDuplicates
        """
        #sys.exit ("Not  implemented")
        print "Not  implemented removeDuplicates"

    def stripSymbols(self):
        """
        PathToDir.stripSymbols
        """
        #sys.exit ("Not  implemented")
        print "Not  implemented stripSymbols"

    def excludePaths(self, pathList):
        """
        PathToDir.excludePaths
        """
        #sys.exit ("Not  implemented")
        print "Not  implemented excludePaths"

    def excludePatterns(self, patternList):
        """
        PathToDir.excludePatterns
        """
        #sys.exit ("Not  implemented")
        print "Not  implemented excludePatterns"
        
    def copyContent (self,  dar,  method,  baseBom = {}):
        """
        Copies fsoList.
        """
        if self.ignored():            
            warning('no contents copied for ignored variable: '+self.varName)
            return
        if not self.fsoList:
            warning('fsoList empty. No files to copy for variable: '+\
                    self.varName)
            return
        rteDirectory = dar.getRteTop()+"/"+self.varName
        
        for i in range(len(self.fsoList)):
            (location,  locFso)  =  self.fsoList[i]
            rteDirI = "%s/path_%d" % (rteDirectory, i)
            # Check for relative paths to directories: in this case 
            # no contents are distributed, and original path is preserved:
            if location[0] == ".":
                self.setups.append(location)
            else:
                self.setups.append(rteDirI)
            # Now copy the contents:
            if locFso:
                locFso.copyContent (dar.getSharedTop(),
                                                 rteDirI,
                                                 dar.getBaseTop(),
                                                 baseBom,
                                                 method)


class LibPath(PathToDir):
    """A runtime environment variable representing a library path."""

    def __init__(self, name, value):
        PathToDir.__init__(self, name,  value)
        self.type = "PathToDir"

    def lddCheck(self):
        """
        LibPath.lddChecks
        """
        print "Not  implemented lddCheck in LibPath class"

    def addSystemPaths(self):
        """
        LibPath.addSystemPaths
        """
        print "Not  implemented addSystemPaths in LibPath class"

    def prependPath(self, valueList):
        """
        Prepends a list of directories and files.
        """
        PathToDir.prependPath(self, valueList)

    def postpendPath(self, valueList):
        """
        Postpends a list of directories and files.
        """
        PathToDir.postpendPath(self, valueList)

        
class BinPath(PathToDir):
    """
    A runtime environment variable representing a binary search path.
    """
    def __init__(self, name, value):
        PathToDir.__init__(self, name,  value)
        self.execuables = []
        self.type = "PathToDir"

    def copyContent (self,  copyDir,  method,  baseBom = {}):
        """
        Copies the contents of copyDir using method.
        """
        PathToDir.copyContent (self,  copyDir,  method,  baseBom)
        if self.varName == "PATH":
            self.setups.append ("${PATH}")

    def prependPath(self, valueList):
        """
        Prepends a list of directories and files.
        """
        PathToDir.prependPath(self, valueList)        

    def postpendPath(self, valueList):
        """
        Postpends a list of directories and files.
        """
        PathToDir.postpendPath(self, valueList)
        
    def lddListCheck(self):
        """
        BinPath.lddListCheck
        """
        print "Not  implemented lddListCheck in BinPath class"


#####################################3
###  Module tests:
#####################################3

if  __name__ == '__main__':
    print "Test create  fso "
    var = LibPath('LDLIBRARYPATH',
                  '/afs/fnal.gov/exp/cms/l/Releases/COBRA/COBRA781/lib/Linux__2.4:/afs/fnal.gov/exp/cms/l/Releases/COBRA/COBRA781/module/Linux__2.4')
    print var
    #globals()[var.type].__dict__[cmd.name](var, cmd.args[1:])
