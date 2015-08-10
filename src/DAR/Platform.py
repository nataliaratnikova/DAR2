#!  /usr/bin/env python
# pylint: disable-msg=W0403

#  Created:  08/30/04  NR.

"""
Class Platform to store information about the working node, and optionally
information about the software bintype
"""
__revision__ = "$Id: Platform.py,v 1.1.1.1 2005/09/28 02:04:23 ratnik Exp $"
__version__ = "$Revision: 1.1.1.1 $"

import popen2

from Utils import Lister

class Platform(Lister):
    """ stores working node info 
    """
    def __init__(self):
        Lister.__init__(self)
        # The command  below must work on linux (UNIX),
        # other platfroms may need more tweaking.
        self._Uname = popen2.popen2("uname -a")[0].readlines()
        self._Hostname = popen2.popen2("hostname")[0].readlines()
        self._Nisdomainname = popen2.popen2("nisdomainname")[0].readlines()
        self._Dnsdomainname = popen2.popen2("dnsdomainname")[0].readlines()
        self._Bintype = ''

    #################################
    # Attribute  methods:
    #################################

    def setBintype(self, strg):
        """
        Set Binary Type

        *strg* : String, name of binary

        """
        print "Setting bintype to:", strg
        self._Bintype = strg

    def getBintype(self):
        """
        Returns the architecture identification string (bintype)
        """
        return self._Bintype

    def getUname(self):
        """Return _Uname"""
        #raise KeyError, "this is a test"
        return self._Uname

    def getHostname(self):
        """Return _Hostname"""
        return self._Hostname

    def getNisdomainname(self):
        """
        getNisdomainnames

        Return the NIS Domain Name
        
        """
        return self._Nisdomainname

    def getDnsdomainname(self):
        """
        getDnsdomainname

        Returns the DNS Domain Name
        """
        return self._Dnsdomainname
