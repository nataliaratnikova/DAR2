"""
    Module Criteria
    Checks criteria that distribution should satisfy
"""
##############################################################
# DAR  Version 2.0
# Natalia Ratnikova  2003-04.
#
# Module Criteria
#  - Check criteria that distribution should satisfy
# 
#         
##############################################################

#import os

__revision__ = "$Id: Criteria.py,v 1.1.1.1 2005/09/28 02:04:23 ratnik Exp $"
__version__ = "$Revision: 1.1.1.1 $"

class Criteria:
    """
    Encompasses Distribution criteria
    """
    # Set default criteria limits for  distribution:
    criteriaDistributionSizeLimit = 600   # size in MB
    criteriaInstallationSizeLimit = 2000  # size in MB
    criteriaTestResultsLimit = 0               # allowed amount of failures
                                                            # without abort

    def __init__ (self):
        # set member variables
        self.distributionSize = 0
        self.installationSize = 0
        self.testResults = 0

    def getSummary(self):
        """
          Print a summary of member variables
        """
        print      "Distribution size:   ", self.distributionSize
        print      "Installation size:   ",  self.installationSize
        print      "Test results:           ",  self.testResults
    
    def checkDistributionSize(self):
        """
          Checks to see if the size of the distribution is
          smaller than the allowable limit
        """
        if self.distributionSize > self.criteriaDistributionSizeLimit:
            return self.distributionSize + \
                   ": LIMIT["+ self.criteriaDistributionSizeLimit+"]"

