#!/usr/bin/env python
# pylint: disable-msg=W0403
"""
Request.py
"""
__version__ = "$Revision: 1.3 $"
__revision__ = "$Id: Request.py,v 1.3 2006/01/18 21:18:53 ratnik Exp $"
    
# DAR  Version 2.0
#
# Natalia Ratnikova  2003-04.
########################

import re
import os
import string
import sys

from SCRAM2DAR import getScramVersion, getReleaseTop, SCRAM, getBaseReleaseName
from SCRAM2DAR import getReleaseMetadata, getProjectName, getVersionTag

from Utils import Lister, infoOut, DARInternalError, warning
from Utils import InputError, Logger

from RTEVariable import RTEVariable, BinPath, PathToFile, PathToDir
from RTEVariable import SimpleValue, LibPath

##################################
# Recognized specfile patterns:
##################################
avariable  = re.compile('(\w+?)\b*=(.*)')
blankLine = re.compile('\s*?$')
# The rest of lines are considered as command.
# Comments are allowed.

class DARcommand(Lister):
    """
    class DARcommand:
      Class to process command lines read from the dar specfile
    """
    # Define static attributes: 
    supportedCommands = [\
        "use", \
        "prependPath", \
        "postpendPath", \
        "excludePattern", \
        "preservePattern", \
        "ignore"]

    useHelp = """
    USAGE:   use   [scram rte | base ]  {arguments}

    This command tells DAR what project, release, or project area needs to be packaged:
    use scram rte  <project name> <release name>
          Example:
          use scram rte COBRA COBRA_7_9_0
    use scram rte <releaseTop>
          Example:
          use scram rte /home/user/work/COBRA_7_9_0

    Use command is also used to specify the base for incremental distributions:
    use base <base dar distribution>
          Example:
          use base /public/base/darballs/pool/COBRA_7_9_0_dar.tar.gz
    """

    prependPathHelp = """
    USAGE:   prepend <var name> <path1>+
    Example: prependPath PATH /bin /usr/bin /usr/local/bin 
    """

    postpendPathHelp = """
    USAGE:   postpend <var name> <path1>+
    Example: postpendPath LD_LIBRARY_PATH /usr/lib /usr/local/lib 
    """

    ignoreHelp = """
    USAGE:   ignore <var name> 
    Example: ignore CMS_DB
    """
    
    excludePatternHelp = """
    USAGE:  excludePattern <var name | ALL> <pattern>+
    Examples:  excludePattern PYTHON_PATH *.pyc  *~
                excludePattern ALL *.html /tmp/ /datafiles/ *.ps  *.pdf /CVS/ /tmp/ /rh73Gcc32Dbg/ /doc/ lib*.a libqt-* /cms132.rz.gz /cms12* /cms131* *.C /rh73Gcc32dbx/ /win32Vc71/
    """
    preservePatternHelp = """
    USAGE:  preservePattern <var name | ALL> <pattern>+
    Example:  preservePattern ALL *.reg /.cache
    """
    
    def __init__(self, line):
        Lister.__init__(self)
        self.line = line
        self.name = ''
        self.args = None
        infoOut ('processing command: '+ line)
        self.processCommand()
        
    def processCommand(self):
        """
        checks a supplied line against the list of supported commands. 
        Called in constructor.
        """
        words = string.split(self.line)
        for name in self.supportedCommands:
            if words[0] == name:
                self.name = words[0]
                self.args = words[1:]
                return
        # If we did not return yet:
        message = "\nCould not find name " + \
                 words[0] + \
                 "\nin the list of supported commands:\n" + \
                 string.join(self.supportedCommands,", ")
        raise InputError, self.line + message

    def help(self):
        """
        DARcommand.help:
        """
        try:
            print self.__class__.__dict__[self.name+'Help']
        except:
            DARInternalError('missing help for '+self.name)

class Request(Lister):
    """
    class Request
      Object of this class keeps the runtime environment, 
      options and any other directives, specifying the request
      for packaging an application. 
      Initial Request object is created based on dar input.
    """
    def __init__(self, darInput, logger):
        Lister.__init__(self) # base constructor
        # Store RTE variables in a dictionary:
        # no two variables can have same name.
        self.logger = logger
        self.rteDict = {}
        self.cmdList = []        
        self._ReleaseMetadata = {}
        self._BaseReleaseName = None
        self._ProjectName = 'undefined'
        self._VersionTag = 'undefined'
        self._DarFile = ''
        # By default we don't  know anything about scram:
        self.scram = None
        self.baseDar = None
        self._Arch = 'arch'
        ##################################
        # Fill up rteDict and cmdList
        ##################################
        infoOut('Reading lines from dar input:')

        for line in darInput:
            # Discard comments and surrounding whitespaces:
            line  =  re.sub('\t*#.*', '', line)
            line  =  string.strip(line)
            ####################
            # Skip blank lines
            ####################
            if blankLine.match(line):
                continue
            ##########################################
            # Process variable settings
            ############################################
            result  =  avariable.match(line)
            if result:
                vName, vValue  =  result.groups()
                # discard surrounding whitespaces:
                vName  =  string.strip(vName)
                vValue  =  string.strip(vValue)
                # Creates a variable object and puts into self.rteDict:
                self.addVariable(vName, vValue)
                continue
            ##################################
            # Consider the rest as commands:
            ##########################################
            cmd = DARcommand(line)
            self.cmdList.append(cmd)
            # Execute commands:
            if cmd.name == "ignore":
                self.executeIgnore(cmd)
                continue
            if cmd.name == "use":
                self.executeUse(cmd)
                continue # next line
            # Check if first command argument is existing variable name.
            # Commands associated with environment variable
            # will use corresponding variable method:
            if self.rteDict.has_key(cmd.args[0]):
                var = self.rteDict[cmd.args[0]]
                self.executeVarCommand(cmd, var)
                continue # next line
            # Check if first command argument is "ALL", and if it is, 
            # execute corresponding method for all variables.
            if cmd.args[0] == "ALL":
                self.executeALLVariables(cmd)
        ###########################################
        # Provide hooks to override PATH settings, in order to control
        # which executables are to be taken into the distribution.
        if self.scram: # i.e. we deal with a scram managed project

            # In scram V0 SCRAMRT_PATH contains additions to PATH, so we use it
            # to override PATH value:
            if self.scram.program == "scram":
                if self.rteDict.has_key('SCRAMRT_PATH'):
                    tmp = self.rteDict['SCRAMRT_PATH'].getValue()
                    self.rteDict['PATH'].setValue(tmp)
                    del tmp
                # Same for LD_LIBRARY_PATH:
                if self.rteDict.has_key('SCRAMRT_LD_LIBRARY_PATH'):
                    tmp = self.rteDict['SCRAMRT_LD_LIBRARY_PATH'].getValue()
                    self.rteDict['LD_LIBRARY_PATH'].setValue(tmp)
                    del tmp
            
            # In scram V1 SCRAMRT_PATH contains default user's PATH settings,
            # so we strip it from the PATH value:
            if self.scram.program == "scramv1":
                tmp = self.rteDict['PATH'].getValue()
                self.rteDict['PATH'].setValue(tmp.replace(':$SCRAMRT_PATH',''))
                del tmp
                # Similar for LD_LIBRARY_PATH:
                tmp = self.rteDict['LD_LIBRARY_PATH'].getValue()
                tmp = tmp.replace(':$SCRAMRT_LD_LIBRARY_PATH','')
                self.rteDict['LD_LIBRARY_PATH'].setValue(tmp)
                del tmp
            # DAR_runtime_PATH overrides both PATH and SCRAMRT_PATH
            # (independent of scram version):
            if self.rteDict.has_key('DAR_runtime_PATH'):
                tmp = self.rteDict['DAR_runtime_PATH'].getValue()
                self.rteDict['PATH'].setValue(tmp)
                del tmp
###########################################
#   Commands executing  functions:
##########################################
    def executeIgnore(self, cmd):
        """
        Request.executeIgnore:
          Checks if variable is defined and calls its ignore method.
        """
        varname = cmd.args[0]
        if self.rteDict.has_key(varname):
            self.rteDict[varname].ignore()
            warning ('variable: '+varname+' is ignored')
        else:
            warning ('could not ignore unknown variable: '+varname)

    def executeUse(self, cmd):
        """
        Request.executeUse
          Executes actions based on a user's input 'use' keyword
          Commands are given as:
            use <cmd> <argument> <input>
            where cmd can be:
              scram - get our DAR input from an existing SCRAM file
                        - if 'rte' is the argument given, we gather the runtime
                          environment from a given relative or absolute path
                        - if 'arch' is given as an argument, we use the
                          scram-defined bintype
              dar     - set some dar information
                        - if 'base' is the input argument, we check to see if
                          the input is an existing darball

                        - if 'file' is the argument given, then we use the given
                          file to get our input
                        - if 'tagname' is given, we set the version tag
                        - if 'projectname' is given, we set the project name                 
        """
        if cmd.args[0]   ==  "scram":
            if cmd.args[1]  ==  "rte":                
                # Get release location, information, etc
                if os.path.isabs(cmd.args[2]):
                    # One can specify top release directory with
                    # absolute path.
                    # Examples:
                    # use scram rte /afs/cern.ch/cms/Releases/ORCA/ORCA_8_4_0
                    # use scram rte /home/user/work/ORCA_8_4_0
                    location = cmd.args[2]
                else:
                    #Or it can be release name preceeded by a project name:
                    #      use scram rte ORCA ORCA_8_4_0
                    #In this case dar gets release top from the scram
                    #database:
                    location = getReleaseTop(cmd.args[2], cmd.args[3])
                if not os.path.isdir(location):
                    cmd.help()
                    message = "could not find release, check command syntax!"
                    raise InputError(cmd.line, message)
                # Choose scram executable name according to scram version used
                # in the project.

                majorVers = getScramVersion(location)[:-1]
                if majorVers[:2] == "V1":
                    self.scram = SCRAM("scramv1")
                elif majorVers[:2] == "V0":
                    self.scram = SCRAM("scram")
                else:
                    sys.exit("""ERROR! do not know how to define scram executable
 for scram version """ + majorVers)
                # Set attributes and additional dar input that scram can get
                # from this location:
                relMeta  =  getReleaseMetadata (location)
                self.setProjectName (getProjectName (relMeta))
                self.setVersionTag (getVersionTag (relMeta))
                self.setBaseReleaseName (getBaseReleaseName(relMeta))
                extraDarInput = self.scram.generateDarInput(location)
                # Process scram generated rte same way as variables
                # from darInput:
                for line in extraDarInput:
                    # process environment variables:
                    result  =  avariable.match(line)
                    if result:
                        vName, vValue  =  result.groups()
                        # discard surrounding whitespaces:
                        vName  =  string.strip(vName)
                        vValue  =  string.strip(vValue)
                        # Creates a variable object and puts into self.rteDict:
                        self.addVariable(vName, vValue)
                        continue
                    # process commands ( variables ignored by
                    # default in SCRAM2DAR):
                    extraCmd = DARcommand(line)
                    self.cmdList.append(extraCmd)
                    if extraCmd.name == "ignore":
                        self.executeIgnore(extraCmd)
                        continue
                    # Check if first command argument is existing variable name.
                    # Commands associated with environment variable
                    # will use corresponding variable method:
                    if self.rteDict.has_key(extraCmd.args[0]):
                        var = self.rteDict[extraCmd.args[0]]
                        self.executeVarCommand(extraCmd, var)
                        continue
                self.setArchitecture(self.scram.platf) # use scram-defined bintype
            if cmd.args[1]  ==  "arch":
                # TO DO: use extra argument to set non-default architecture, 
                # e.g. "use scram arch <some arch>".
                print "WARNING: Not implemented command: use scram arch"
                
        elif cmd.args[0]   ==  "dar":
            if cmd.args[1]   ==  "base": 
                # Command syntax :  use dar base <base dar ball>
                self.baseDar = cmd.args[2]
                # Do quick checks just  to  make sure baseDar could  be a dar;
                # return immediately if base distribution is not found:
                # It can be dar installation directory or a dar
                # distribution file:
                if os.path.isdir(self.baseDar):
                    infoOut('Use Base DAR installation from a directory:'+\
                             self.baseDar)
                elif os.path.isfile(self.baseDar):
                    infoOut('Use Base DAR distribution from file:'+\
                             self.baseDar)
                else:
                    # Lookup for base darball in the pool
                    infoOut('Base DAR is not a file or a directory: '+\
                             self.baseDar)
                    infoOut('Will be looked up later in the dar shared pool ')
            if cmd.args[1] == 'file':
                # Command syntax :  use dar file <darball path (or LFN?)>
                self.setDarFile(cmd.args[2])
            if cmd.args[1] == 'tagname':
                # Command syntax :  use dar tagname <version tag>
                # TODO: add a check that tag contains allowed characters only
                self.setVersionTag (cmd.args[2])
            elif cmd.args[1] == 'projectname':
                # Command syntax :  use dar projectname <project tag>
                # TODO: add a check that project name contains
                # allowed characters only
                self.setProjectName (cmd.args[2])
            if cmd.args[1]  ==  "arch":
                # use extra argument to set non-default architecture, 
                # e.g. "use scram arch <some arch>".
                infoOut('set Architecture to ' + cmd.args[2])
                self.setArchitecture(cmd.args[2])
        else:
            warning('unrecognized command syntax: ', cmd.line)

    def addVariable(self, key, value):
        """
        Request.addVariable:
          Add an environment variable to the list
        """
        infoLine = "Add variable "+key+"  =  "+value+"\ntype="
        # Variable types identified by name :
        if key  ==  'LD_LIBRARY_PATH':
            infoOut(infoLine+'LibPath')
            self.rteDict[key] = LibPath(key, value)
            return
        if key  ==  'DAR_runtime_PATH':
            infoOut(infoLine+'BinPath')
            self.rteDict[key] = BinPath(key, value)
            return
        if key  ==  'PATH':
            infoOut(infoLine+'BinPath')
            self.rteDict[key] = BinPath(key, value)
            return
        if key  ==  'SCRAMRT_PATH':
            infoOut(infoLine+'BinPath')
            self.rteDict[key] = BinPath(key, value)
            return
        # Variable types identified by value:
        if os.path.isfile(value):
            infoOut(infoLine+'PathToFile')
            self.rteDict[key] = PathToFile(key, value)                
            return
        if os.path.isdir(value):
            infoOut(infoLine+'PathToDir')
            self.rteDict[key] = PathToDir(key, value)
            return
        if re.search(':', value):
            # probably a list of paths, but could also be a url, etc
            # just for test now treat all like directory paths.
            infoOut(infoLine+'PathToDir')
            self.rteDict[key] = PathToDir(key, value)
            return
        # The rest is considered a simple value type:
        infoOut(infoLine+'SimpleValue')
        self.rteDict[key] = SimpleValue(key, value)        

    def executeALLVariables(self, cmd):
        """
        Request.executeALLVariables:
          Something that needs to  be done for all variables
        """        
        # Such method should be defined in the  base class:
        try:
            for variable in self.rteDict.values():
                RTEVariable.__dict__[cmd.name](variable, cmd.args[1:])
        except KeyError:
            DARInternalError('Could not find method '+\
                               cmd.name+' in '+variable.type)
        except:
            DARInternalError('while executing ' + cmd.name +
                             ' for ALL variables.')

    def executeVarCommand(self, cmd, varCmd):
        """
        Request.executeVarCommand:
        """
        try:
            # looks for corresponding method in the variable class            
            varCmd.__class__.__dict__[cmd.name](varCmd, cmd.args[1:])
        except KeyError:
            # looks for same method in the parenting class
            try:
                globals()[varCmd.type].__dict__[cmd.name](varCmd, cmd.args[1:])
            except KeyError:
                DARInternalError('Could not find method '+\
                                   cmd.name+' in '+varCmd.type)
            except:
                DARInternalError('doing' + cmd.name +
                                 'for' + varCmd.__class__.__name__)
        except:
            DARInternalError("doing " + cmd.name +
                             " in " + varCmd.__class__.__name__)

    def showRTE(self):
        """
        Request.showRTE:
        """
        print self.rteDict

    def showDARcommands(self):
        """
        Request.showDARcommands:
        """
        print self.cmdList

    #########################
    # Attribute set/get  functions:
    #########################
    def setProjectName(self, name):
        """
        Request.setProjectName:
        """
        self._ProjectName = name
        
    def getProjectName(self):
        """
        Request.getProjectName
        """
        return self._ProjectName

    def setDarFile(self, name):
        """
        Request.setDarFile
        """
        self._DarFile = name
        
    def getDarFile(self):
        """
        Request.getDarFile:
        """
        return self._DarFile

    def setVersionTag(self, name):
        """
        Request.setVersionTag
        """
        self._VersionTag = name
        
    def getVersionTag(self):
        """
        Request.getVersionTag
        """
        return self._VersionTag

    def setBaseReleaseName(self, name):
        """
        Request.setBaseReleaseName
        """
        self._BaseReleaseName = name
        
    def getBaseReleaseName(self):
        """
        Request.getBaseRelease
        """
        return self._BaseReleaseName

    def setArchitecture(self, name):
        """
        sets Architecture
        """
        self._Arch = name
        
    def getArchitecture(self):
        """
        returns requested architecture
        """
        return self._Arch

###############################################
if  __name__ == '__main__':
    try:
        if len(sys.argv)>1:
            inputFile = sys.argv[1]
        else:
            inputFile = '/home/natasha/WORK/DAR-2/dev/DAR-2/src/test/darInput'
        if not os.path.isfile(inputFile):
            raise InputError(inputFile, "no such inputFile")
        # Read input from inputFile containing scram runtime environment output
        f = open(inputFile, "r")        
        R = Request(f.readlines(), Logger('/tmp/DAR2-request.log'))
        R.showRTE()
        R.showDARcommands()        
    except InputError, e:
        print "InputError occured:"
        print "     expression  = ", e.expression
        print "     message  = ", e.message 
