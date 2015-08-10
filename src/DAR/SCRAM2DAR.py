#!/usr/bin/env python
"""
SCRAM2DAR.py
"""
__version__ = "$Revision: 1.1.1.1 $"
__revision__ = "$Id: SCRAM2DAR.py,v 1.1.1.1 2005/09/28 02:04:23 ratnik Exp $"
    
# DAR  Version 2.0
#
# Natalia Ratnikova  2003-04.
########################
# SCRAM to DAR interface 
import os
import re
import sys
import popen2
import string

from Utils import warning, process, Session, stop, usageError, infoOut

########################################
#  Getting SCRAM release information routines
########################################
def getScramVersion(releaseTopDir):
    """ Returns scram version used by the project, according to
    the contents of config/scram_version file in the project area
    """
    if not os.path.isdir(releaseTopDir):
        sys.exit("Not a directory " + releaseTopDir)
    versFile = releaseTopDir+'/config/scram_version'
    # TODO: add checks.
    inputFile = open(versFile, 'r')
    return inputFile.readline()[:-1]

def getReleaseTop(projectName, releaseName):
    """Returns the location of the release installation"""
    # First try scramv1 list as more selective:
    infoOut("looking for " + projectName + " " + releaseName + " release top")
    cmd = 'scramv1 list -c ' + projectName
    infoOut("Trying " + cmd + " ... ")
    for line in popen2.popen2(cmd)[0].readlines():
        proj, rel, loc = string.split(line)
        if (proj, rel) == (projectName, releaseName):
            return loc
    # Now lookup all project's releases using scram: 
    cmd = 'scram listcompact ' + projectName
    infoOut("Trying " + cmd + " ... ")
    for line in popen2.popen2(cmd)[0].readlines():
        proj, rel, loc = string.split(line)
        if (proj, rel) == (projectName, releaseName):
            return loc
    # If we still did not find a proper release, it must be user's error.
    sys.exit("SCRAM2DAR.getReleaseTop: could not find " + str(releaseName) + \
             " release. \n     Hints: check your request and scram architecture.")
            
def getReleaseMetadata(releaseTopDir):
    """
    getReleaseMetadata:
      Collects info from scram internal files
    """
    # These are scram hardcoded default paths: 
    envFile = releaseTopDir+'/.SCRAM/Environment'
    releaseMetadata = {}

    inputFile = open(envFile, 'r')
    for line in inputFile.readlines():
        process(line, releaseMetadata)
    return releaseMetadata

def getBaseReleaseName(releaseMetadata):
    """getBaseReleaseName"""
    if releaseMetadata.has_key('RELEASETOP'):
        return releaseMetadata['RELEASETOP']
    else:
        return '' # empty  line

def getProjectName(releaseMetadata):
    """getProjectName"""
    return releaseMetadata['SCRAM_PROJECTNAME']

def getVersionTag(releaseMetadata):
    """getVersionTag"""
    return releaseMetadata['SCRAM_PROJECTVERSION']


#  Getting SCRAM release information routines

class SCRAM:
    """SCRAM"""
    ### TO RE-DO !!!!!!!!!!
    ### Use Session instead popen2 !!! 

    def __init__(self, scramExe):
        self.program = scramExe 
        try:
            self.version = popen2.popen2(self.program+\
                                       " version")[0].readlines()[0][0:-1]
        except:
            sys.exit("ERROR: Failed in SCRAM.__init__"+\
                     "while trying to get scram version."+\
                     "\nCheck your scram executable: "+self.program)
        self.platf = popen2.popen2(self.program+" arch")[0].readlines()[0][0:-1]
        # Pattern may depend on scram version, this is valid for scram V0_20_0:
        if self.program == "scram":
            self.rtePattern = re.compile('(\w+?=)"(.*)";\012')
            self.scramrtPattern = re.compile('(\SCRAMRT_\w+?)=')
        elif self.program == "scramv1":
            self.rtePattern = re.compile('export (\w+?=)"(.*)";\012')
            self.scramrtPattern = re.compile('export (\SCRAMRT_\w+?)=')
        else:
            DARInternalError('scram executable \"'+self.program+'\" is not supported') 

        # This is SCRAM and CMS specific list of variables
        # that are always ignored :
        #self.autoIgnoreList = ['LOCALRT', 'CMS_PATH', 'GCCEXECPREFIX']
        self.autoIgnoreList = ['LOCALRT', 'CMS_PATH', 'GCC_EXEC_PREFIX']

    def getScramRte(self, fromDir):
        """
        Returns the file object with the runtime environment as set by scram
        """
        cmd = "cd "+fromDir+"; "+self.program+" runtime -sh"
        rte = popen2.popen2(cmd)[0].readlines()
        return  rte 

    def getScramArch(self):
        return self.platf

    def generateDarInput(self, loc):
        """
        Produces RTE list part of the dar specfile
        based on scram runtime command
        """
        darRte = []
        for line in self.getScramRte(loc):
            # Transform  scram output  line into dar input  line 
            result = re.subn(self.rtePattern, r'\g<1>\g<2>', line)
            
            if  result[1] == 1:
                darRte.append(result[0])
            # Add also all SCRAMRT variables to automatically ignored list:
            scramrtMatch = self.scramrtPattern.match(line)
            if scramrtMatch:
                self.autoIgnoreList.append(scramrtMatch.groups()[0])

        # Extend dar input to automatically ignored list.
        for var in self.autoIgnoreList:
            darRte.append('ignore '+var)

        # More default dar specfile commands can be added here.
        return darRte

    def getToolList(self, session, projectDir):
        """
        Returns an array of pairs : (toolname, toolversion) for all  tools in the project  configuration.
        Works for  scram V0  and V1.  
        """
        # change to the proper directory and get tool list output:
        session.run('pushd '+projectDir)
        toolsDict = {}
        (toolListOut, stat) = session.run(self.program+' tool list')
        if (stat  != '0'):
            session.run('popd')
            warning(string.join(toolListOut))
        else:
            scramHeader=1
            for line in toolListOut:
                if line[:5] == '+++++' : 
                    # end of the  scram header lines
                    scramHeader=0
                    continue
                if not scramHeader:
                    result=line.split()
                    if result:
                        toolsDict[result[0]]= result[1]
        return toolsDict
    
    def getToolRteList(self, session, projectDir, toolname):
        """
        This is a helping function to quickly get the list of
        runtime variables set by the tool.
        Since other tools may set the same variables, one
        should not rely on the produced list only, when
        specifying the list of ignored variables
        """
        runtimeVars=[]
        # change to the proper directory
        # get tool info first:
        session.run('pushd '+projectDir)
        (toolInfoOut, stat) = session.run(self.program+' tool info '+toolname)
        if (stat  != '0'):
            session.run('popd')
            # TODO:  raise an exception, if e.g. tool does not  exist... 
            warning(string.join(toolInfoOut))
        else:
            session.run('popd')
            # extract all assignment statements:
            allVars = []
            for line in toolInfoOut:
                match = string.find(line, '=')
                if match  != -1:
                    allVars.append( line[:match])
            # Get the runtime environment:
            session.run('pushd '+projectDir)
            (runtimeOut, stat) = session.run(self.program+' ru -sh')
            session.run('popd')
            # compare the list of runtime environment variables with
            # the tool assignments and get list of the runtime
            # environment variables set by the tool:
            runtimeVars = []
            # get varname from the  export  statements :    "export varname;"
            exportStatement = re.compile('export (.*);')            
            for line in runtimeOut:                
                res = exportStatement.match(line)
                if res and  (res.groups()[0] in allVars):
                    runtimeVars.append(res.groups()[0])
        return runtimeVars

# Unit  tests ############################
if  __name__ == '__main__':    
    topdir = '/afs/fnal.gov/exp/cms/l/Releases/COBRA/COBRA_7_9_0'
    topdir = '/afs/fnal.gov/exp/cms/l/CMSSW/CMSSW_0_0_1_pre5'
    #topdir = '/cms/sw/Releases/COBRA/COBRA_8_0_2'
    #topdir = '/cms/sw/Releases/COBRA/COBRA_8_4_2'
    print "Testing   scram for topdir ",  topdir
    scramVers=getScramVersion(topdir)
    if scramVers[:2] == "V0":
        scram = SCRAM('scram')
        toolName = 'gcc'
    elif scramVers[:2] == "V1":        
        scram = SCRAM('scramv1')
        toolName = 'cxxcompiler'
    else:
        sys.exit("ERROR! could not  define scram executable for  scram version "+scramVers)
    s = Session()
    toolRte = scram.getToolRteList(s,  topdir,  toolName)
    print "RTE for tool "+toolName+":\n", toolRte
    
    # unit test for getToolList:
    toollist=scram.getToolList(s, topdir)
    print "tool list for ", topdir, "is:"
    print toollist

    stop()
    darInput = scram.generateDarInput(topdir)
    print scram.autoIgnoreList
    relMeta = getReleaseMetadata(topdir)
    print "SCRAM release metadata:",  relMeta
    project, release = ('ORCA', 'ORCA_8_7_1')
    print "Testing   scram for project  release: " ,  project,  release
    location = getReleaseTop(project, release)
    print "test: scram tool list "
