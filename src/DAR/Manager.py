#!/usr/bin/env python
# pylint: disable-msg=W0403
###################################
#  Created:  05/05/04  NR.
#
# Main  class to  create  DARball.
#
#  This class is responsible for 
# - operate the request,
# - derive corresponding  distribution contents,
# - calculate, save and compare various criteria,
# - run application tests in new runtime environment,
# - produce necessary metadata,
# - and finally create the darball.
#
# Development comments :
#  05/14/04              - removed refdbdar and related classes 
#  05/05/04      
#                        - moved some refdbdar code here
#                           
#
###########################################################

"""
Manager.py
    The Manager module  is responsible for
        - operating the request
        - deriving corresponding distribution contents
        - calculating, saving and comparing various criteria
        - running application tests in the new runtime environment
        - producing necessary metadata
        - creating the darball
"""

__version__ = "$Revision: 1.1.1.1 $"
__revision__ = "$Id: Manager.py,v 1.1.1.1 2005/09/28 02:04:23 ratnik Exp $"


# system  includes

import os
import sys
import time
import string

from Utils import infoOut, Logger, Lister, notWritable, spaceLeft, InputError
from Utils import DARInternalError, notReadable, readFileFromArchive, cleanup
from Utils import noteSize, usageError, commands, getDarVersion
from Utils import getVerbose, setVerbose

from Metadata import Metadata, loadMetadata
from Request import Request

from Structure import Structure, getBOMFileName, getMetaDataFile
from Structure import getDarDirName, getTopEnvName, getSetupScriptBasename

class Manager(Lister):
    """
    class Manager:
       Main class to create DARball.
       - processes initial request,
       - decides whether it should  be an incremental distribution. For example, if the
         base distribution for the same release is found in the dar shared pool, and user's
         top release directory is in private development area.

       If yes:
         - creates incremental distribution, including a reference to the base release darball,
           and the private part of the application.
       If not:
         - creates a private base darball and incremental part, and generates a request for a
           public base darball. 

       The base  creation of a base darball includes following steps: 
         - create RTE directory structure with simlinks according to request,
         - create metadata,
         - calculate criteria for inital request,
         - check  if calculated  createria are satisfactory
         - run tests (optional)
         - adjust request and repeat the procedure until satisfied (optional in interactive, or
           semi-interactive mode)
         - create and save darball 
       """
    # Defaults:

    def __init__(self, darInput, pltf=None, cnf=None):        
        """
        __init__
          Initializes DAR Manager apects common to both create and install mode.
        """        
        Lister.__init__(self)

        # Set defaults:
        self.darballSuffix = '_dar.tar.gz'

        # and initialize variables:
        self.baseBomDict = {}  # need for incremental darball
        self.darpool = None    # 
        self.dar = None # need for creating darball
        
        self.config = cnf
        infoOut('Validating DAR configuration ...')
        if getVerbose():
            print "CONFIGURATION:", self.config
        # Check that dar shared pool is set up, exists and has right permissions:
        # DAR shared pool is to lookup for a base dar distributions and/or
        # installations . 
        if self.config.has_key("dar_shared_pool"):
            self.sharedPool = self.config["dar_shared_pool"]
        else:
            sys.exit("ERROR:dar shared pool is not defined in the configuration")
        if self.config.has_key("dar_dist_pool"):
            self.distPool = self.config["dar_dist_pool"]
        else:
            sys.exit("ERROR: dar dist pool is not defined in the configuration")
        if self.config.has_key("dar_inst_pool"):
            self.instPool = self.config["dar_inst_pool"]
        else:
            sys.exit("ERROR: dar inst pool is not defined in the configuration")

        # Check that dar tmpdir is set, exists, and has right permissions:
        if self.config.has_key("dar_tmp_dir"):
            self.tmpdir = self.config["dar_tmp_dir"]
        else:
            sys.exit("ERROR: dar_tmp_dir is not defined in the configuration")
        if notWritable(self.tmpdir):
            sys.exit(notWritable(self.tmpdir))
            
        # Each time when dar is called, it creates a new build directory
        # in tmpdir pool, using a unique datestamp:
        self.blddir = self.tmpdir+'/'+str(time.time())

        # Start logger and pre-set log files:
        self.logdir = self.blddir + '/logfiles' # one dir for all logfiles
        self.timingLog = Logger(self.logdir+'/session.timing')
        self.sessionStdoutLog = self.logdir+'/session.stdout'
        self.sessionHistoryLog = self.logdir+'/session.history'

        # Create necessary directories and files:
        os.makedirs(self.blddir)
        os.makedirs(self.logdir)
        for logfile in (self.sessionStdoutLog,  self.sessionHistoryLog):
            infoOut('Creating ' + logfile + ' file')
            open(logfile, 'w').close()

        # Get platform info:
        self.platform = pltf

        self.timingLog('Completed configuration and setup ')

        # Create a request 
        self.currentRequest = Request(darInput, self.timingLog)
        self.timingLog('Created request object')

        # Initialize dar metadata
        self.darMeta = Metadata()
        self.darMeta.setDarVersion(getDarVersion())
    
        # Get release/version metadata from request and
        # put them into Metadata container:
        self.darMeta.setDarInput(darInput)
        self.darMeta.setBaseReleaseName(self.currentRequest.getBaseReleaseName())
        self.darMeta.setProjectName(self.currentRequest.getProjectName())
        self.darMeta.setVersionTag(self.currentRequest.getVersionTag())

        # Architecture
        self.darMeta.setArchitecture(self.currentRequest.getArchitecture())
        
    def prepareDistribution(self, method = 'copy'):
        """
        Manager.prepareDistribution:
          Creates DARball structure according to current request, using
          copy, or link method.
        """
        # Check  how  much  space is  left in tmp dir,
        # where the darball will be built:
        spaceLeft(self.tmpdir)
        self.timingLog('Checked space left in '+self.tmpdir)

        # If incremental darbal was requested, get its metadata,
        # and fill up base bomdictionary
        baseDar = self.currentRequest.baseDar
        self.darMeta.setBaseDar(baseDar)
        
        if baseDar:
            if os.path.isdir(baseDar):
                # This should be an installation directory:
                bomFile = baseDar+'/' + getBOMFileName()

                if os.path.isfile(bomFile):
                    # Create base bom dictionary directly from file 
                    for entry in open(bomFile,'r').readlines():
                        # a list of lines
                        (md5, entryPath) = string.split(entry)
                        self.baseBomDict[entryPath] = md5
                else:
                    raise InputError(baseDar,
                                    'Could not find ' +
                                     getBOMFileName() + ' here.')
            else:
                if os.path.isfile(baseDar):
                    # This should be a DARball:
                    baseDarball = baseDar
                else:
                    # This should be a release tag of a base darball
                    # available from the dar pool.
                    # Lookup for base darball in the distribution pool:
                    
                    if notReadable(self.distPool):
                        sys.exit(notReadable(self.distPool))
                    baseDarball = self.findBaseDarball(self.distPool, baseDar)
                    if not baseDarball:
                        sys.exit( 'Could not find base distribution for ' \
                                  +baseDar+' in '+self.sharedPool)
                        
                # Create base bom dictionary on the flight from the archive:
                result = readFileFromArchive(baseDarball, getBOMFileName())

                for entry in string.split(result,'\n'):
                    md5, entryPath = string.split(entry)
                    self.baseBomDict[entryPath] = md5

        # Now create DAR directory structure:
        self.dar = Structure(self.blddir, self.currentRequest,
                             method, baseBom = self.baseBomDict)

        self.timingLog('Created DAR in ' + self.blddir +
                       ' using ' + method + ' method')
        instDir = self.dar.getTopInstDir()
        if method == 'copy':
            self.timingLog('Counted install. size ' +
                           'before cleanup in shared dir')
            # Make cleanup and create BOM only for the FSO image (shared 
            # between the environment variables):
            cleanup(self.dar.getSharedTop(),
                    os.path.join(self.dar.getTopInstDir(), getBOMFileName()))
            self.timingLog('Removed duplicates and created BOM for ' +
                           self.dar.getSharedTop())
        size = noteSize(instDir)
        self.timingLog('Counted size after cleanup in ' +
                       self.dar.getSharedTop())
        self.darMeta.setInstallationSize(size)
        # fakeScram()
        # including scram runtime command, which may replace setup scripts.
        self.saveMetadata(os.path.join(self.dar.getTopInstDir(),
                                       getMetaDataFile()))
        
        # - saves into metadata file info about creation of a darball,
        # project conifguration info. Adds a spec file (and darInput in
        # scram mode). DAR info and its source code go here.
        self.createReadmeFile()
        # DAR info, istallation instructions, reference to documentation.
        # self.rememberSize()

    def installApplication(self, installDir, testmode):
        """
        Manager.installApplication
          Installs the application by performing the following steps:
            - checks to see if the installation directory is writable
            - loads metadata
            - checks if enough disk space is available
            - checks to see if this is an incremental installation
              - looks for the base disribution for this release
            - checks for previous installation of this package
              and checks the md5sum <not implemented>
            - unpacks the installation package
            - publishes package metadata
            - sets up the environment scripts and runs setup scripts
            - creates links and checks installation size
        """
        if notWritable(installDir):
            sys.exit(notWritable(installDir))
        # Absolutize path if needed:
        if not os.path.isabs(installDir):
            installDir = os.path.abspath(installDir)
        # Extract metadata from distribution:
        metadata = loadMetadata(getMetaDataFile(),
                                archive = self.currentRequest.getDarFile())

        infoOut('Loaded DAR metadata from '+self.currentRequest.getDarFile())
        # If in test mode, print out users info and exit:
        if testmode:
            print metadata.userInfo()
            return
        # Check  that  there is enough space in the installation directory:
        available = spaceLeft(installDir)
        installSize = float(metadata.getInstallationSize())

        if available < installSize:
            sys.exit('Not enough space on the disk!\n Installation size: ' \
                     + str(installSize) +
                     ' KB\n Available: ' +
                     str(available) + ' KB')

        self.timingLog('Checked space left in '+installDir)
        ##########################################
        #   Handling  incremental DARballs:
        ##########################################
        # Check if darball metadata contain a reference to a base dar:
        baseDar = metadata.getBaseDar()
        if baseDar:
            infoOut("This is  incremental distribution based on "+baseDar)
            # This is an incremental darball, so 
            # we need matching base installation.
            baseInstallation = self.currentRequest.baseDar
            if  not baseInstallation:
                usageError ('Please specify a base .')
                # Lookup for base installation in the installation pool:
                # baseInstallation = self.findBaseInstallation(self.distPool,
                #                                           baseDar)
                # if not baseInstallation:
                #    sys.exit( 'Could not find base installation for ' +
                #                   baseDar + '
                #                   in '+self.sharedPool)
            infoOut("(todo)Verifying base installation "+baseInstallation)
        ##########################################
        #   General actions for all DARballs:
        ##########################################
        # Check if the installation already exists:
        releaseInstTop = os.path.join(installDir,
                                      metadata.getVersionTag(),
                                      metadata.getArchitecture())
        if os.path.exists( releaseInstTop):
            # TODO: validate the installation using  md5sum and
            # tell user the results
            sys.exit("ERROR: You already have installation here: \n   " \
                     +releaseInstTop+"\nExiting ....\n")
        # Unpack darball
        infoOut('Unpacking '+self.currentRequest.getDarFile()+' .... ')
        unpackCommand = 'tar -xz -C ' + \
                        installDir + ' -f ' + \
                        self.currentRequest.getDarFile()

        (status, out) = commands.getstatusoutput(unpackCommand)
        
        # Check that in unpacked into toInstallDir as expected:
        if status: # failed
            if out:
                # save command output in the logfile:
                unpackLogfile = os.path.join(self.logdir, 'dar_unpack.log')
                tarlog = open(unpackLogfile, 'w')
                tarlog.write('Output from unpacking command:\n' + \
                         unpackCommand + '\n' + out )
                tarlog.close()
            sys.exit ('Unpacking failed with exit status ' + status + \
                      '\nOutput can be found in \n' + unpackLogfile )
        elif not os.path.isdir(releaseInstTop):
            sys.exit ('Can not  find  '+releaseInstTop)            
        # Link to a base installation for incremental darballs 
        if baseDar:
            infoOut("Create a link to base installation:\n ln -s "
                     +baseInstallation+'/shared '+releaseInstTop+'/base')
            os.symlink(baseInstallation+'/shared', releaseInstTop+'/base')
        # Set up environment scripts:
        infoOut("Setting up the installation")
        templateStub = os.path.join(releaseInstTop, getSetupScriptBasename())
        newSetupScriptStub = os.path.join(releaseInstTop, 'envSetup')
        helpText = self.updateSetupScripts(\
                   templateStub, \
                   releaseInstTop, \
                   newSetupScriptStub )

        # For compatibility with the old Production tools:
        oldSetupScriptStub = os.path.join(releaseInstTop,
                                          metadata.getVersionTag() + '_env')
        self.updateSetupScripts(\
                   templateStub, \
                   releaseInstTop, \
                   oldSetupScriptStub )

        # Move script templates to the DAR admin directory. 
        #infoOut('Removing setup scripts templates ...')
        cmd = 'mv ' + templateStub + '.*sh' + ' ' \
              + installDir + '/' + getDarDirName()
        (status, out)=commands.getstatusoutput(cmd)
        if status != 0: # did not succeed
            DARInternalError("In installApplication: " +
                             "doing command" + cmd +
                             "\ncommand output :\n" + out)
        
        
        #infoOut("(todo) Do md5sum check of BOM in resulting installation")
        #infoOut("(todo) If successful, " +
        #        "register installation in publishing service ")
        self.publishMetadata(installDir + '/' + getDarDirName())
        # Publish installation metadata:
        self.publishMetadata(installDir + '/' + getDarDirName())

        #Print out runtime environment setup help (and exit):
        infoOut(helpText)
        infoOut("Installation completed.")
        
    def updateSetupScripts(self, template, installDir, newScriptStub):
        """
        Manager.updateSetupScript
          Copies the setup scripts for the different shell environments
          and prints instructions for using them
        """
        # Look into using shutils.copyfile(src,dest)
        # For bash shell:
        envScriptSh = newScriptStub + '.sh'
        fileRead = open(template + '.sh')
        contents = fileRead.readlines()
        contents.insert(0, 'export ' + getTopEnvName() +
                        '=\"' + installDir +'\";\n')
        fileRead.close()
        fileWrite = open(envScriptSh, 'w')
        fileWrite.writelines(contents)
        fileWrite.close()
        # For tcsh/csh shell:
        envScriptCsh = newScriptStub + '.csh'
        fileRead = open(template + '.csh')
        contents = fileRead.readlines()
        contents.insert(0, 'setenv ' + getTopEnvName() +
                        ' \"'+installDir+'\";\n')
        fileRead.close()
        fileWrite = open(envScriptCsh, 'w')
        fileWrite.writelines(contents)
        fileWrite.close()
        helpText = """
To set the runtime environment:
------------------------------
in  csh or tcsh:
         source """+envScriptCsh+"""
in  sh, bash, zsh:
         .  """+envScriptSh+"""
"""
        return helpText

    
    def publishMetadata(self, metadataDir):
        """
        Publishing step after successful install
        """
        # Currently it simply removes .DAR directory,
        # in future is could update a simple database of dar installations
        cmd = 'rm -rf '+ metadataDir        
        (status, out)=commands.getstatusoutput(cmd)
        if status != 0: # did not succeed            
            DARInternalError("In publishMetadata: " +
                             "doing command" + cmd +
                             "\ncommand output :\n" + out)
        
    def createReadmeFile(self):
        """
        Manager.createReadmeFile:
          Include DAR info, installation instructions, reference to
          documentation for the user  to read after manually
          unpacking the darball.
          <not implemented>
        """
        print "Creating users README file in the darball (not implemented)" 
        

    def rememberSize(self):
        """
        FSO only reflects the size of the shared space.
        Without the RTE structure, and in incremental installations,
        size above the base does not contribute to the total
        installation size
        """
        # Do we still need this?  The size is  attribute of  the globalFso,
        # and it can be saved in Metadata. 
        # Yes, we need, because fso only reflects the size of the shared part,
        # without rte structure , and because  for incremental dar files 
        # from the base do not contribute into the total installation size.
        #infoOut( "Counting and remembering the size of installation..." )
        #size = noteSize(self.blddir)
        #if size:
        #    self.darMeta.setInstallationSize(int(string.split(output)[0]))
        #    infoOut ("Installation size is " + size + " KB")
        #else:
        #    warning('Could not get size of ' + self.blddir)
        pass    
            
    def saveAndQuit(self, darFile = 'useDefault'):
        """
        Creates the final DARball and returns.
        This is called when the user is satisfied with the result,
        or when the criteria are satisfied (if in non-interactive mode).
        If successful, it will return the name of the final darball that
        was created, otherwise it will return 'None'.
        """

        if darFile == 'useDefault':
            darFile = self.blddir + "/" +\
                      self.darMeta.getVersionTag() +\
                      "." + self.currentRequest.getArchitecture() +\
                      self.darballSuffix
        else:
            darFile = self.blddir + "/" +\
                      self.currentRequest.getDarName() +\
                      self.darballSuffix

        tarCmd = string.join ( [
            'tar -cz -f', darFile,
            '-C',
            os.path.join(self.blddir, self.dar.getTopInstDir()),
            getDarDirName(),
            '-C', self.blddir, self.darMeta.getVersionTag()
            ])
        infoOut("Creating DAR distribution in " +
                self.blddir + "using tar command:")
        infoOut(tarCmd)

        (status, out) = commands.getstatusoutput(tarCmd)
        if status == 0: # successfull 
            infoOut( "Created " + darFile)
            self.timingLog('Created darball: ' + darFile)
            return darFile
        else:
            infoOut( "Creation of dar file failed!\n " + out)
            return None
        
    def setDarPool(self, location):
        """
        Manager.setDarPool:
          Mutator method to set the DAR Pool location
        """
        self.darpool = location

    def findBaseDarball(self, darPool, releaseName):
        """
        Manager.findBaseDarball
          Finds a proper darball in the darpool,
          based on the project release name
        """
        for filename in os.listdir(darPool):
            if filename == releaseName+self.darballSuffix:
                return darPool+'/'+filename

    def changeRequest(self):
        """
        Manager.changeRequest
          <not implemented>
        """
        print "Changing  request (not implemented)"

    def runTest(self):
        """
        Manager.runTest
          <not implemented>
        """
        print "Running  test  (not implemented)"

    def checkCriteria(self):
        """
        Manager.checkCriteria:
          <not implemented>
        """
        print "Checks if criteria  are  satisfied (not implemented)"

    def getCriteria(self):
        """
        Manager.getCriteria:
          <not implemented>
        """
        print "Calculating  criteria   (not implemented)"

    def findBest(self):
        """
        Manager.findBest:
          <not implemented>
        """
        print "Finding request with best criteria  (not implemented)"

    def runDebug(self):
        """
        Manager.runDebug:
          <not implemented>
        """
        print "Running debug test  (not implemented)"

    def saveMetadata(self, metadataFile):
        """
        Manager.saveMetadata
          Saves metadata information to a given file
        """
        print "saving DAR metadata"
        self.darMeta.saveMetadata(metadataFile)
