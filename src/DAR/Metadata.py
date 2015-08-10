#!/usr/bin/env python
"""
Metadata.py
  Class  for  storing  dar  metadata: 
  - request and software application info
  - DARBall creation details
"""
__version__ = "$Revision: 1.1.1.1 $"
__revision__ = "$Id: Metadata.py,v 1.1.1.1 2005/09/28 02:04:23 ratnik Exp $"
    
# Class  for  storing  dar  metadata:
# details  request and  software application info
# and the details of creating the darball 
#
#
# pylint: disable-msg=W0403

import string
import os
import pickle
import imp

from Utils import Lister, Logger, infoOut, readFileFromArchive, strong

class Metadata(Lister):
    """
    class Metadata:
      Structure to hold DAR metadata. Handles three types of data:
        1) general darball info to be shown to the user 
        2) data used internally by dar
        3) various data may be needed for troubleshooting problems 
    """
    def __init__(self):
        # Currently all metadata are put together in this one class.
        # Later on they can be split more conveniently depeniding
        # on the methods required.
        ###############################
        self._ProjectName = "" 
        self._BaseReleaseName = "" 
        self._VersionTag = "" 
        self._ToolConfig = "" 
        self._Platform = "" 
        self._CreationTime = "" 
        self._HostName = "" 
        self._DarVersion = "" 
        self._DarOptions = "" 
        self._InstallationSize = 0
        self._LogFile = "" 
        self._UserName = "" 
        self._BaseDar = None

    def userInfo(self):
        """
        Metadata.userInfo
        """
        def header(headerString):
            """
            Metadata.userinfo.header
              returns a nicely formatted header string
            """
            #return "\n"+"="*35+"\n|"+headerString+":\n"+"-"*35+"\n"
            return "\n" + strong(headerString + ":") + "\n"
        output = \
                 header('Contents of DAR request spec file')+\
                 str(self._DarInput)+\
                 header('Application information')+"""
Base DAR :  \t"""+ str(self._BaseDar)+"""
Project name:  \t"""+ str(self._ProjectName)+"""
Base release name:\t""" +str(self._BaseReleaseName)+"""
Version Tag:   \t""" +str(self._VersionTag)+"""
Platform:      \t""" +str(self._Platform)+\
                 header('Tool configuration Info')+str(self._ToolConfig)+\
                 header('DARball creation details')+"""
Start time:\t"""+str(self._CreationTime)+"""
Host name:\t"""+str(self._HostName)+"""
User name:\t"""+str(self._UserName)+\
                 header('DAR version')+str(self._DarVersion)+\
                 header('DAR options')+str(self._DarOptions)+\
                 header('Installation size')+\
                 str(self._InstallationSize)+' KB'+\
                 header('Log file')+str(self._LogFile)+"""
                 """ # adds the EOL
        return output

    def saveMetadata(self, metadataFile):
        """
        Metadata.saveMetadata
          Saves metadata info using the pickle module
        """
        # Save  to  file:
        # outputFile = open (file,  'w')

        infoOut('Saving dar metadata in file:    '+metadataFile) 

        # This saves human readable user info:
        #f.write(self.userInfo())
        # This writes object's listing provided by  class Lister:
        # f.write(str(self))
        # This saves the instance  in  python internal object stream format
        pickle.dump(self, open(metadataFile, 'w'))
    
    ####################
    #  Attribute methods 
    ####################

    def setDarInput(self, listOfLines):
        """
        Metadata.setDarInput:
          Sets the _DarInput
        """
        #  SCRAM managed project  name :
        self._DarInput = string.join (listOfLines,  '')
        
    def getDarInput(self):
        """
        Metadata.getDarInput
        """
        return self._DarInput
    
    def setProjectName(self, name):
        """
        setProjectName
        """
        #  SCRAM managed project  name :
        self._ProjectName = name
        
    def getProjectName(self):
        """
        getProjectName
        """
        return self._ProjectName
    
    def setBaseReleaseName(self, name):
        """
        setBaseReleaseName
        """
        # Release name: for base distribution  same as version tag, 
        # for incremental  distributions theoretically it may differ.
        self._BaseReleaseName = name
        
    def getBaseReleaseName(self):
        """
        getBaseReleaseName
        """
        return self._BaseReleaseName

    def setVersionTag(self, name):
        """
        setVersionTag
        """
        # Release name 
        self._VersionTag = name
        
    def getVersionTag(self):
        """
        getVersionTag
        """
        return self._VersionTag
        
    def setLogFile(self, name):
        """
        setLogFile
        """
        self._LogFile = name
    def getLogFile(self):
        """
        getLogFile
        """
        return self._LogFile

    def setDarVersion(self, versionString):
        """
        setDarVersion
        """
        self._DarVersion = versionString
        
    def getDarVersion(self):
        """
        getDarVersion
        """
        return self._DarVersion    

    def setArchitecture(self, name):
        """
        set architecture string 
        """
        # Release name
        self._Platform = name
                 
    def getArchitecture(self):
        """
        get architecture identification string
        """
        return self._Platform

    def setBaseDar(self, baseDarString):
        """
        setBaseDar
        """
        self._BaseDar = baseDarString
        
    def getBaseDar(self):
        """
        getBaseDar
        """
        return self._BaseDar  


    def setInstallationSize(self, integerSize):
        """
        setInstallationSize
        """
        # Integer can handle sizes upto at least 0.5 TB
        self._InstallationSize = integerSize
        
    def getInstallationSize(self):
        """
        getInstallationSize
        """
        return self._InstallationSize


###################################
#  Metadata handling functions:
###################################

def loadMetadata( metadataFile,   archive = None):
    """
    loadMetadata
    """
    # Extracts metadata file from the distribution archive:
    #    if os.path.isfile (archive):
    result = readFileFromArchive(archive,  metadataFile)
    metadata = pickle.loads(result)
    return metadata
    
###################################
#  Module tests:
###################################

if  __name__ == '__main__':
    darInput = string.split("""
SimpleValue1 =  abra-kadabra
SimpleValue2 = 123
PathToFile = /home/natasha/.signature
PathToDir = /scratch/natasha/www
SEALKEEPMODULES = true
PATH = /afs/fnal.gov/files/code/cms/l/Releases/ORCA/ORCA811/bin/Linux__2.4:/afs/fnal.gov/exp/cms/l/Releases/COBRA/COBRA781/bin/Linux__2.4:/afs/fnal.gov/exp/cms/l/Releases/IGNOMINY/IGNOMINY180/bin/Linux__2.4
prependPath LD_LIBRARY_PATH /home/natasha/lib allkhaf/asl
postpendPath LD_LIBRARY_PATH blabla
ignore PATH""", 
                           "\n")
    tmpDir = "/tmp/natashaTestMetadata"
    os.mkdir(tmpDir)
    logger = Logger(tmpDir+'/logger')
    logger('started test')
    logger('created request')
    metadata = Metadata()
    metadata.setLogFile(logger.logfileName())
    #print metadata.userInfo()
    logger('finished Metadata unit-test')    
    print metadata
    metadata.saveMetadata(tmpDir+'/metadataFile')

