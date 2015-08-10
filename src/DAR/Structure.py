#!/usr/bin/env python
# pylint: disable-msg=W0403
"""
Structure.py
         - responsible for the distribution internal structure.
         - provides general methods used by the DARmanager object
"""
__version__ = "$Revision: 1.1.1.1 $"
__revision__ = "$Id: Structure.py,v 1.1.1.1 2005/09/28 02:04:23 ratnik Exp $"

import os,  os.path

from Utils import Lister, infoOut
from RTEVariable import PathToDir, PathToFile

# Some hardcoded names: 

def getDarDirName ():
    """
    Returns the name of the DAR admin directory
    """
    return ".DAR"

def getMetaDataFile ():
    """
    Name and relative location of dar Matadata file
    """
    return os.path.join(getDarDirName(), 'darMetadata')

def getBOMFileName():
    """
    Name and relative location of dar BillOfMaterial file
    """
    return os.path.join(getDarDirName(), 'Manifest.txt')

def getSetupScriptBasename():
    """
    Returns setup script stub
    """
    return 'template_env'

def getTopEnvName():
    """
    returns the name of env. variable to specify the top
    of the installation directory in the environment setup script
    """
    return 'DAR_INST_TOP'

class Structure(Lister):
    """
      Responsible for internal structure of DAR distribution
    """

    def __init__ ( self,  toDir,  rqst,  method,  baseBom = {} ):
        """
        Defines and builds the internal structure of the DAR
        distribution.
        Returns the stub of the environment setup scripts, i.e. relative
        location in the distribution without shell-specific suffix.
        """
        Lister.__init__(self) # call base class constructor  

        # top installation directory:
        self.instTop = os.path.join(toDir, rqst.getVersionTag(), rqst.getArchitecture())

        # here the global fso image will go:
        self._SharedTop = os.path.join(self.instTop + '/shared')

        # top of runtime environment based structure:
        self._RteTop = os.path.join(self.instTop + '/rte')

        # link to top of base installation structure:
        self._BaseTop = os.path.join(self.instTop + '/base')

        os.makedirs(os.path.join(self.instTop, getDarDirName()))

        # Stub for templates of environment setup scripts:
        self._EnvScriptStub = os.path.join(self.instTop, getSetupScriptBasename())

        # Create DARball contents:
        self._BuildDarStructure(rqst,  method,  baseBom)
        
    def _BuildDarStructure(self,  rqst,  method,  baseBom = {}):
        """
        Copies Distribution contents, creates setup scripts, and fills
        up the BOM dictionary.
        """
        # create directories for dar internal stuff        
        os.makedirs(self.getRteTop())
        os.makedirs(self.getSharedTop())

        shScript  =  open(self._EnvScriptStub + '.sh',  'w')
        cshScript  =  open(self._EnvScriptStub + '.csh',  'w')
        for varname, variable in rqst.rteDict.items():
            if isinstance( variable,  PathToFile):
                if not variable.ignored():
                    variable.createFso(variable.varValue) 
                    variable.filename = os.path.basename(variable.varValue)

            if isinstance( variable,  PathToDir):
                if not variable.ignored():
                    variable.createFso()
                
            variable.copyContent (self,  method,  baseBom)

            # create csh env script:
            shScript.write(variable.setEnv(self.instTop,
                                              '${' + getTopEnvName() + '}',
                                              shell = 'sh'))
            
            cshScript.write(variable.setEnv(self.instTop,
                                               '${' + getTopEnvName() + '}',
                                               shell = 'csh'))
            
            rqst.logger('Created DAR structure for ' + varname)
        # close both files:
        shScript.close()
        cshScript.close()

    ####################
    # Attribute methods:
    ####################

    def getTopInstDir(self):
        """
        Returns top installation directory 
        """
        return self.instTop
    
    def getSharedTop(self):
        """
        Returns top of shared directory structure, needed for FSO. 
        """
        return self._SharedTop
    
    def getRteTop(self):
        """
        DAR.getRteTop
        """
        return self._RteTop
    
    def getBaseTop(self):
        """
        DAR.getBaseTop
        """
        return self._BaseTop

    def getEnvScriptStub(self):
        """
        Returns Envscript  Stub=location+name-suffix
        """
        return self._EnvScriptStub
