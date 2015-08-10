#!/usr/bin/env python
# pylint: disable-msg=W0403
"""
_DARInterface_

Simple Python API for creating and installing DAR balls that can be used
at runtime to build and install DARballs on the fly in batch jobs.

"""
__version__ = "$Revision: 1.1.1.1 $"
__revision__ = "$Id: DARInterface.py,v 1.1.1.1 2005/09/28 02:04:23 ratnik Exp $"
__author__ = "evansde@fnal.gov"


import os
import sys

from Manager import Manager
from Platform import Platform



def createStandardDAR(scramRtePath, darTagName):
    """
    _createStandardDAR_

    Create a standard non-incremental darball from the scram rte path
    provided, and create a dar file with the tagname provided.

    """
    darConf = []
    darConf.append("use scram rte  %s\n" % scramRtePath)
    darConf.append("use dar tagname %s\n" % darTagName)
    config = {
        "dar_shared_pool" : os.getcwd(),
        "dar_dist_pool" : os.getcwd(),
        "dar_inst_pool" : os.getcwd(),
        "dar_tmp_dir" : os.getcwd(),
        }
    manager = Manager( darConf, cnf=config, pltf=Platform() ) 
    manager.prepareDistribution('copy')
    manager.checkCriteria()
    darFile = manager.saveAndQuit()
    
    if not os.path.exists(darFile):
        raise RuntimeError, "Darfile not created: %s " % darFile
    return darFile



def installStandardDAR(darfile, installDir):
    """
    _installStandardDAR_

    Installation of a standard DARball
    
    """
    config = {
        "dar_shared_pool" : os.getcwd(),
        "dar_dist_pool" : os.getcwd(),
        "dar_inst_pool" : os.getcwd(),
        "dar_tmp_dir" : os.getcwd(),
        }
    
    darConf = []
    darConf.append("use dar file %s\n" % darfile)

    manager = Manager( darConf, cnf=config, pltf=Platform() )
    manager.installApplication( installDir, None )

    return installDir


    
class DARInterface:
    """
    _DARInterface_

    Interface class to the DAR tool python API

    """
    def __init__(self):
        """
        This class acts as a namespace and doesnt need to be inited,
        since all the methods are static
        """
        msg = "Error: DARInterface class does not need to be initialised"
        raise RuntimeError, msg

    createStandardDAR = staticmethod(createStandardDAR)
    installStandardDAR = staticmethod(installStandardDAR)
    
