#! /usr/bin/env python
#
# RefDB2DAR interface in python 
# Created:  April, 15-17, 2003  NR
# Modified: June, 2003 

import os
import re
import sys
import time
import string
import popen2
import readline

from Utils import infoOut, Lister, notWritable, Session, Logger
from Utils import process, warning
from SCRAM2DAR import SCRAM, getScramVersion, getReleaseTop
from Packager import DAR2Packager

#from refdbdar_util import *
#from Packager import *

class RefDBDAR(Lister):
    """ Main class for refdbdar interface"""
    def __init__(self, tmpdir, program):
        """ Makes necessary checks and sets RefDBDAR attributes"""

        #check that CMS environment  is set:
        if not os.environ.has_key('CMS_PATH'):
            message = """CMS_PATH variable is not defined.
Please set CMS environment"""
            sys.exit(message)            
        self.tmpdir = tmpdir
        infoOut( 'temporary directory is '+self.tmpdir)
        if notWritable(self.tmpdir):
            sys.exit(notWritable(self.tmpdir))

        # Collect a list of warnings:
        self.allWarnings = []

        # Start session to execute shell commands
        self.s=Session()

        # Create every time new build directory in tmpdir pool
        # using datestamp :
        self.blddir = self.tmpdir + '/' + str(time.time())
        self.s.run('mkdir -p ' + self.blddir)

        # Define log files (all in one directory):
        self.logdir = self.blddir + '/logfiles/'
        self.s.run('mkdir -p ' + self.logdir)
        self.timingLog = Logger(self.logdir+'session.timing')
        self.sessionStdoutLog = self.logdir+'session.stdout'
        self.sessionHistoryLog = self.logdir+'session.history'

        self.programPath, self.programName=os.path.split(program)
        self.dar = self.programPath+'/dar2'
        infoOut( 'dar executable is '+self.dar)
        (out, stat) = self.s.run(self.dar+' -v ') # display dar version 
        if stat != "0":
            message="""dar executable failed
Please check DAR availability and configuration"""
            self.error(message)

        infoOut("current dar version is: "+out[len(out)-1][:-1])

        self.cvsbase = ':pserver:anonymous@cmscvs.cern.ch:/cvs_server/repositories/'
        infoOut('cvs server basename is ' + self.cvsbase )

        # Initialize required attributes:
        self.numExe = 0
        self.executables = []
        self.applList = [] # allow zero applications 
        self.geomFilesList = []
        self.geomPathList = []
        self.darHooks = {}
        self.DARRemoveTools = []
        self.DARIgnoreFile = None
        # Log current time
        self.timingLog('RefDBDAR configured')

    def error(self, string, status=1): # status should be an integer!
        logfile=self.blddir+'/session.stdout'
        print '\033[1mRefDBDAR ERROR: \033[0m', string
        self.saveLog()
        sys.exit(status)

    def exception(self,where):
        out= "exception in", where, \
             "\nType:", sys.exc_type, \
             "\nValue:", sys.exc_value
        # Treat any exception is an error:
        self.error(out)

    def parseRequest(self,file):
        # Disable  try:
        if 0 == 0 :
        #try:
            f = open(file,'r')
            input = {}    
            for line in f.readlines():
                process(line, input)
            # Store input values from the request in attributes
            # (mapping to the RefDB used variable names):
            self.project = input['Application']
            self.release = input['Version'    ]
            # Handle multiple geometry files:
            if input.has_key("NumberOfGeometryFiles"):
                self.geomFileNum = int(input['NumberOfGeometryFiles'])
                for i in range(self.geomFileNum):
                    self.geomFilesList.append(Geometry(input,str(i)))
                    # DO check right away during parsing
                    infoOut("Validating file "+self.geomFilesList[i].filePath +" ...")
                    if not (self.geomFilesList[i]).valid():
                        self.error("Invalid geometry file: "+self.geomFilesList[i].filePath)
            # Add paths to multiple Geometry versions.
            if input.has_key("NumberOfGeometryXMLversions"):
                self.geompath_num=int(input['NumberOfGeometryXMLversions'])
                for i in range(self.geompath_num):
                    self.geompath_list.append(GeometryPath(input,str(i)))
            # Get darfile related info: 
            self.darball=DARball(input) # an object            
            # List of Executables to be searched in runtime PATH:
            if input.has_key("ExecutablesList"):
                self.executables=string.split(input['ExecutablesList'],";")
            # List of applications to  be built from sources:
            if input.has_key("NumberOfExecutables"):
                self.numExe = int(input['NumberOfExecutables'])
                for i in range(self.numExe):
                    if input.has_key('Application_'+str(i)):
                        self.applList.append(Application(input,str(i)))# each an object
            if not self.numExe:
                raise "zero_num_exe"
            # Define a few DAR hooks that will extend scram runtime environment
            # by setting special DAR variables
            for name in input.keys():
                # DAR_PRE_ hook:
                if name[0:8] == "DAR_PRE_":
                    self.darHooks[name]=input[name]
                # DAR_POST_ hook:
                if name[0:9] == "DAR_POST_":
                    self.darHooks[name]=input[name]
                # DAR_ROOTRC hook:
                if name=="DAR_ROOTRC":
                    self.darHooks[name]=input[name]                
                # DAR_IGNORE_FILE - a separate hook that helps to pass the file with the
                # runtime environment variables to be ignored in dar:
                if name == "DAR_ignore_file":
                    self.DAR_ignore_file = input[name]
                # get list of tools to be removed from the project
                # configuration before packaging:
                if name == "DAR_remove_tools":
                    self.DAR_remove_tools = string.split(input[name],";")
            
        # For all SCRAM managed projects use DAR2: 
        self.packager = DAR2Packager(self) 
        self.timingLog('input file processed')
    def cleanDir(self,dir):
        # verbosity control is taken care in session
        self.s.run('rm -rf '+dir)
    def saveLog(self):
        lf=open(self.sessionStdoutLog,'w')
        lf.writelines(self.s.allOut)
        lf.close()
        lf=open(self.sessionHistoryLog,'w')
        lf.writelines(self.s.commands)
        lf.close()
        infoOut("Session logfiles can be found in the directory "+self.logdir)

class DARball(Lister):
    """ Distribution related info from the RefDB request """
    def __init__(self,input):
        self.bintype = input['Architecture']
        self.comment = input['Comments']
        self.darname = input['DARFileName']
        self.status  = input['DARStatus'  ]
        self.release = input['Version'    ]
        self.project = input['Application']
        self.idNum  = input['DARFileID'  ]
        # URLs of files to be added to the users CWD:
        self.extra_url = []
        # Getting url of the external xml file from the comment:
        xml_url_pattern = re.compile('.*(http://.*\.xml).*')        
        res = xml_url_pattern.match(self.comment)
        if res:
            self.extra_url.append(res.group(1))
        # Support for both scram and scramv1: 
        # First  get scram  version for this release:
        majorV = getScramVersion(getReleaseTop(self.project, self.release))[:2]
        if majorV == "V0":
            self.scram = SCRAM('scram')
        elif majorV == "V1":
            self.scram = SCRAM('scramv1')
        else:
            sys.exit("ERROR! could not define scram executable for" + \
                     "scram version " + majorV)

        # Get current architecture.
        # Check to be added here:
        # - scram will create project area even if release is not available
        # for this platform 
        # - architecture should comply with the current system 
        # Get current architecture from scram 
        infoOut( 'scram architecture is '+ self.scram.getScramArch())

class Application(Lister):
    """ Application specific info from the RefDB request """
    def __init__(self, input, num):
        self.cvsTag = input['Version_'   +num]
        self.exename = input['Executable_'+num]
        self.testdir = input['Package_'   +num]

class Geometry(Lister):
    """ Geometry file specific info from the RefDB request """
    def __init__(self, input, num):
        self.file_vers = input['GeometryFileName_'+num]
        self.file_size = input['GeometryFileSize_'+num]
        self.file_path = input['GeometryFilePath_'+num]
        self.file_cksum = input['GeometryFileCksum_'+num]        
    def valid(self):
        if (self.file_cksum,self.file_size)==string.split(popen2.popen2('cksum '+self.file_path)[0].readlines()[0])[:-1]:
            print "OK"
        else:
            return (self.file_cksum,self.file_size)
class GeometryPath(Lister):
    """ Path to Geometry projects"""
    # Attention :  num  supposed to  be a string 
    def __init__(self, input, num):
        self.path=input['Geometry_PATH_'+num]
        self.version=input['GeomPATHversion_'+num]
