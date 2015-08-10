#! /usr/bin/env python
# refdbdar module for  creating  cmsim  distributions
# Created:  July, 1, 2003  NR
# Modified: May, 19, 2004 NR :  CMKIN_packager

import os
import re
import sys
import time
import string
import popen2
import fnmatch
import readline
import commands

from Utils import infoOut, stop
from SCRAM2DAR import SCRAM

class DAR2Packager:
    """ Packages scram managed projects applications using dar2 """
    def __init__(self, RefDBDar):
        self.ref = RefDBDar
        self.usersCWD = '' # will be set later, when the path is defined
        self.usersCWDname = "users_cwd" 
        # Maps directory names to executables found in those directories:
        self.rtePATHdict = {}
        # List of directories to be added to DAR runtime PATH:
        self.darRuntimePathList = []
        # Hardcode exclude pattern here for now:
        self.excludeCommand = string.join (["excludePattern ALL ",
                                   "*.pyc",
                                   "*.html",
                                   "datafiles",
                                   "*.ps",
                                   "*.pdf",
                                   "CVS",
                                   "tmp",
                                   "rh73_gcc32_dbg",
                                   "doc",
                                   "*/lib*.a",
                                   "*/libqt-*",
                                   "cms132.rz.gz",
                                   "*/cms12*",
                                   "*/cms131*",
                                   "*.C",
                                   "rh73_gcc32dbx",
                                   "win32_vc71",
                                   "/usr/bin/*",
                                   "/usr/lib/*",
                                   "/lib/*", "\n"])

        self.preserveCommand = "preservePattern ALL  */*.reg   */.cache \n"
        # Dar2 spec file:
        self.specFileName = os.path.join(self.ref.blddir, \
                                         self.ref.darball.idNum + '.spec')
        self.specFile = open(self.specFileName, 'w')
        infoOut('Created ' + self.specFileName)

    def addGeometryPATHs(self, toDir):
        if self.ref.geomPathNum:
            for eachPath in self.ref.geomPathList: 
                cmd = 'mkdir -p ' + toDir + "/" + eachPath.version
                if self.ref.s.run(cmd)[1] != '0':
                    self.ref.error("Could not create directory:\n  "+cmd)
                cmd = 'cp -r ' + eachPath.path + ' ' + toDir + "/" + \
                      eachPath.version
                if self.ref.s.run(cmd)[1] != '0':
                    self.ref.error("Could not copy geometry path. " +\
                                   "Command failed:\n  "+cmd)
    def addGeometryFiles(self,toDir):        
        if self.ref.geomFileNum:
            # put all files into one directory :
            cmd = 'mkdir -p '+toDir
            if self.ref.s.run(cmd)[1] != '0':
                    self.ref.error("Could not create directory for " + \
                                   "geometry files. Command failed:\n " + cmd)
            for geom in self.ref.geom_files_list:
                if not geom.valid():
                    self.ref.error("Invalid Geometry file: "+geom.file_path)
                cmd='cp -p '+geom.file_path+' '+to_dir
                if self.ref.s.run(cmd)[1] != '0':
                    message = "Could not copy geometry file. " + \
                              " Command failed:\n   "+cmd
                    self.ref.error(message)
    def buildApplications(self):
        # Create project development space:
        cmd = 'export CVSROOT=' + self.ref.cvsbase + self.ref.darball.project
        self.ref.s.run(cmd)
        self.ref.s.run('cd ' + self.ref.blddir)
        
        cmd = self.ref.darball.scram.program + ' project '+ \
              self.ref.darball.project + ' ' +\
              self.ref.darball.release
        if self.ref.s.run(cmd)[1] != '0':
            self.ref.error("Creating project area for " + \
                           self.ref.darball.darname + \
                           " failed\n\nPlease check request in input file " +\
                           "and availability of the release!")
            
        self.ref.s.run('cd ' + self.ref.darball.release)
        patchline = "use scram rte " + \
                    os.path.join(self.ref.blddir, self.ref.darball.release) + \
                    "\n"
        self.specFile.write (patchline)
        infoOut("Added to  spec File : \n" + patchline)
        #--------------------------------------------------------------------------
        #  Add special DAR hooks:
        #--------------------------------------------------------------------------
        for name in self.ref.darHooks.keys():
            infoOut("USING DAR HOOK " + name + "\n")
            self.specFile.write(name + "=" + self.ref.darHooks[name])

        #--------------------------------------------------------------------------
        #  Add Geometry files:
        #--------------------------------------------------------------------------
        if self.ref.geomFilesList:
            geometryFilesTempLocation=self.ref.blddir+"/added_to_dar"
            self.specFile.write("Geometry_files=" + geometryFilesTempLocation)
            infoOut('Added to spec file:\n' + patchline)
            # Add Geometry files to the corresponding dir:
            self.addGeometryFiles(geometryFilesTempLocation)

        #--------------------------------------------------------------------
        #  Add XML Geometry versions:
        #--------------------------------------------------------------------
        # Geometries are requested by RefDB directly rather than through the
        # runtime environment, as expected by DAR, so we create new variable
        # in the Runtime file:
        if self.ref.geomPathList:
            geomDir = self.ref.blddir + "/Geometry"
            patchline="Geometry_PATH_ROOT=" + geomDir
            self.specFile.write(patchline)
            infoOut('Added to spec file:\n' + patchline)
            # Add XML Geometries to the corresponding dir:
            self.addGeometryPATHs(geomDir)
            
        #--------------------------------------------------------------------
        #  Add OSCAR specific variables and settings:
        #--------------------------------------------------------------------
        if (self.ref.darball.project =='OSCAR'):
            oscarExtraDict={}

            # There is a new environment variable to set "MagneticFieldPath",
            # which should be set to the output of `scram tool tag geometry 
            # GEOMETRY_BASE`.  --TW.
            cmd = self.ref.darball.scram.program + ' tool tag geometry GEOMETRY_BASE'
            (out, stat) = self.ref.s.run(cmd) 
            oscarExtraDict['MagneticFieldPath'] = out[0]

            # The physics tables can be read at startup, rather than calculated
            # every time, thereby speeding up the jobs. This means having the 
            # contents of OSCAR_3_6_0/src/Data/QGSP_PhysicsTables packaged with
            # the darfile, and for the application to know where to find them 
            # (so presumably another environment variable).   --TW.
            
            oscarExtraDict['PhysicsTables']='$(RELEASETOP)/src/Data/QGSP_PhysicsTables'        

            # These two lines will add pre-setup environment scripts to clear all  *_PATH variables
            # on the installation sites
            self.ref.s.run('export DAR_PRE_SET_CSH='+os.getcwd()+'/scripts/presetup.csh')
            self.ref.s.run('export DAR_PRE_SET_SH='+os.getcwd()+'/scripts/presetup.sh')

            # These variables and respective contents will now be added in OSCAR darfiles
            # (independent of release name, or RefDB request) unless they are already defined
            #  in the OSCAR project Runtime file.
            for var in oscarExtraDict.keys():
                # TODO: add a check if variable was already defined
                infoOut('Set additional variable ' + var + ' to ' + oscarExtraDict[var])
            
        #-------------------------------------------- 
        # Construct a path to the  srcdir
        #-------------------------------------------
        applSrcDir = string.join([self.ref.blddir, \
                                  self.ref.darball.release, \
                                  'src'],'/')
        #-------------------------------------------- 
        # Remove tools from the configuration
        #-------------------------------------------
        # Attention: this may break the build. 
        self.ref.DARRemoveTools.append('oracle')
        infoOut('WARNING: removing oracle tool ')
        if self.ref.DARRemoveTools:
            infoOut("going to remove following tools:\n" + \
                              string.join(self.ref.DARRemoveTools, ', '))

            # get list  of all  tools first:
            scram = SCRAM(self.ref.darball.scram.program)
            allTools = scram.getToolList(self.ref.s, applSrcDir)
            for tool in self.ref.DARRemoveTools:
                # Check if tool exists in the configuration:
                if allTools.has_key(tool):
                    # remove the tool:
                    (out, stat)=self.ref.s.run(self.ref.darball.scram.program + \
                                               ' tool remove ' + tool)
                    if ( stat != "0" ):
                        self.ref.error("failed to remove tool "+tool+". STOP.")
                    else:
                        infoOut(tool + ' tool is successfully removed.')
                else:
                    infoOut('Tool ' + tool + ' is not found in the  configuration')
        #-------------------------------------------- 
        # Building or copying executables: 
        #-------------------------------------------
        # Set scram runtime environment (without local bindir yet):
        self.ref.s.run('cd '+applSrcDir)
        cmd = 'eval `' + self.ref.darball.scram.program + ' runtime -sh`'
        (out,stat) = self.ref.s.run(cmd)
        # Search for ready executables in the runtime PATH :
        infoOut("Check availability of requested executables: " + \
                          string.join(self.ref.executables, ", "))
        for exe in self.ref.executables:
            (out, stat) = self.ref.s.run("which "+exe)
            if (stat != "0"):
                # File not found in PATH, check if there are build instructions:
                found = None
                for appl in self.ref.applList:
                    if appl.exename == exe:
                        found = exe
                if not found:
                    self.ref.error("""
Can not satisfy request for executable: """ + exe + """
Not found in the runtime PATH, no build instructions provided.
Please fix the request file !
""")
                else:
                    infoOut("""Executable not found in PATH: """ + \
                                      exe + """
           Will be built from sources according to request""")
            else:
                # Delete build request for existing executable:
                for buildRequest in self.ref.applList:
                    if buildRequest.exename == exe:
                        self.ref.applList.remove(buildRequest)
        # Now build the rest of requested applications from sources: 
        if self.ref.applList:
            for appl in self.ref.applList:
                self.ref.s.run('cd ' + applSrcDir)
                self.ref.s.run('cvs -q co -r ' + appl.cvsTag + ' ' + appl.testdir)
                self.ref.s.run('cd ' + appl.testdir)
                self.ref.s.run('touch *')
                self.ref.s.run(self.ref.darball.scram.program + ' build ' + \
                               appl.exename)
                # Add application to executables list, if not already there:
                if not appl.exename in self.ref.executables:
                    self.ref.executables.append(appl.exename)
        
            # Set scram runtime again to add local bindir:
            self.ref.s.run('eval `' + self.ref.darball.scram.program + \
                           ' runtime -sh`')
        # Now collect all paths containing requested executables to
        # $DAR_runtime_PATH.
        darPathDir=self.ref.blddir+"/DAR_runtime_PATH"
        self.ref.s.run("mkdir " + darPathDir)
        infoOut("Collecting executables in " + darPathDir )
        num=0
        for exe in self.ref.executables:
            (out, stat) = self.ref.s.run("which " + exe)
            if (stat == "0"):
                exeFound=out[0][:-1]
                cmd = "cp -vp " + exeFound + \
                      " " + darPathDir
                (out, stat) = self.ref.s.run(cmd)
                if stat == "0":
                    num = num + 1 
                else:
                    stop()
                del exeFound
            else:
                # normally we should not be here: any error should break earlier:
                self.ref.error('executable missing from the runtime PATH: ' +\
                               exe)
                
        # Check that all executables are created (the quantity only)
        infoOut( "All executables:")
        if num != self.ref.numExe:
            self.ref.error('Wrong number of executables!Should be:' + \
                           str(self.ref.numExe) + "; Found:" + \
                           str(num))
        self.ref.timingLog('build applications finished')
        
        # Add DAR_runtime_PATH to project's Runtime file to be shipped with
        # the runtime environment.        
        patchline="DAR_runtime_PATH=" + darPathDir + "\n"
        self.specFile.write(patchline)
        infoOut('Added following line to'+self.specFileName+'\n'+patchline)
    
    def createDistribution(self):
        infoOut("Creating dar distribution... ")
        ignore_list=["GCC_EXEC_PREFIX", "CMS_PATH", "SEAL"]
        if (self.ref.darball.project == 'ORCA'):
            ignore_list=ignore_list +["CMS_DB"]
        if (self.ref.darball.project == 'COBRA'):
            ignore_list=ignore_list +["CMS_DB"]

        # Ignore stuff for compact OSCAR distribution... (nothing added currently)
        for i in range(len(ignore_list)):
            self.specFile.write('ignore ' + ignore_list[i]+"\n")
            
        # Take care of excluded patterns in the spec file:
        self.specFile.write(self.excludeCommand)
        infoOut("added to spec File: " + self.excludeCommand)

        # Take care of preserved  patterns in the spec file:
        self.specFile.write(self.preserveCommand)
        infoOut("added to spec File: " + self.preserveCommand)

        # Specify darball name:
        tagnameCommand = "use dar tagname " + \
                      self.ref.darball.darname + "\n"
        self.specFile.write(tagnameCommand)
        infoOut("added to spec File: " + tagnameCommand)

        cmd = string.join([self.ref.dar,   \
                           '-c', self.specFileName ])
                           
        self.specFile.close()
        (out, stat)=self.ref.s.run(cmd)
        if (stat != "0"):
            self.ref.error('Dar file creation failed.')
        self.ref.timingLog('dar ball created')
        # Clean out distribution directory, keeping only darfile and build
        #dir_to_remove=self.ref.tmpdir+'/'+self.ref.darball.darname
        #self.ref.cleanDir(dir_to_remove)
        #self.ref.timingLog('removed temporary directory '+dir_to_remove)
        #infoOut('removed temporary directory '+dir_to_remove)
        self.ref.saveLog()
        infoOut('Done! Created distribution in '+self.ref.tmpdir+'\n')
        
