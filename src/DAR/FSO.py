# pylint: disable-msg=W0403

"""
FSO.py
  - creates and manipulates file system objects
    (* collection of directories and files *)
"""

__revision__ = "$Id: FSO.py,v 1.1.1.1 2005/09/28 02:04:23 ratnik Exp $"
__version__ = "$Revision: 1.1.1.1 $"

import os
import shutil
import fnmatch

from Utils import DARInternalError, warning, shortcut, canonicalPath
from Utils import strong, commonPath, infoOut, Bunch, convertPatternList
from Utils import stripPath, Lister
#from Utils import stop, debug

def _ValidPath(fsoPath):
    """
    Returns boolean value which determines whether the given path exists
    """
    return os.path.exists(fsoPath)

def createFSO(fsoPath, arg):
    """
    Attempts to return/create a valid FSO object and return it
    """
    # arg is a darUtil.Bunch object used to pass extra arguments and flags
    # down to each entry
    try:
        return FSO(fsoPath, arg)
    except InvalidPath:
        warning('invalid  path: '+fsoPath+'; no FSO created...')
        return None

class InvalidPath(Exception):
    """
    Represents Exception that occurs with an invalid path
    """
    pass

class Entry(Lister):
    """
    Representation for a file or directory object
    """
    def __init__(self, entryPath, arg):
        Lister.__init__(self)
        self.path = entryPath
        self.name = os.path.basename(canonicalPath(entryPath))
        self._Excluded = None
        self._Preserved = None        
        self._AlwaysKept = None

        # first check  the stat: 
        try:
            self.stat = os.stat(entryPath)
        except OSError:
            self.stat = None
            warning(' stat failed for this entry:\n  '+entryPath)
            self.type = 'stat_failed'

        if self.stat:
            # treat directories and files separately :
            if os.path.isfile(entryPath):
                self.type = 'file'
            elif os.path.isdir(entryPath):
                self.type = 'dir'
            else:
                DARInternalError( "path is not a file nor a directory: "+ \
                                  entryPath)
            self.checkAgainstPatterns(entryPath, arg)

    def checkAgainstPatterns(self, entryPath, arg):
        """
        Check against pattern lists:
        Process pattern lists in the priority order: preserve, alwaysKeep,
        exclude and return immediately after first match
        """
        for pattern in arg.preserveList:
            if fnmatch.fnmatch(entryPath, pattern):
                self._Preserved = pattern
                break
        if not  self._Preserved:
            for pattern in arg.alwaysKeepList:
                if fnmatch.fnmatch(entryPath, pattern):
                    self._AlwaysKept = pattern
                    break

        if not  self._Preserved and  not self._AlwaysKept:
            for pattern in arg.excludeList:
                if fnmatch.fnmatch(entryPath, pattern):
                    self._Excluded = pattern
                    break
        # You  probably do not want to  add any more actions below,  as
        # by now many entries are already returned.

    def foundInBase(self, baseBomDict):
        """
        Entry.foundInBase:
          If  found in the base bom, returns the md5 of the file
        """
        key = '.'+self.path
        if baseBomDict.has_key(key):
            #debug('found in base ', self.path)
            return baseBomDict[key]
        
    def isfile(self):
        """
        Entry.isfile:
          Returns true if this Entry object represents a file
        """
        return self.type[-4:] == 'file'

    def isdir(self):
        """
        Entry.isdir:
          Returns true if this Entry object represents a directory
        """
        return self.type[-3:] == 'dir'

    def excludedByPattern(self):
        """
        Entry.excludedByPattern:
        Returns whether or not this Entry should be excluded
        from the installation
        """
        return self._Excluded

    def preservedByPattern(self):
        """
        Entry.preservedByPattern:
        """
        return self._Preserved

    def alwaysKeptByPattern(self):
        """
        Entry.alwaysKeptByPattern:
        """
        return self._AlwaysKept

    def smartCopy(self, dest, method='copy'):
        """
        Entry.smartCopy:
         Copies a instanced Entry.
         If it is a directory, we make a new directory,
         If it is a file, we link to it
        """
        # Excluded entries are not copied, no matter
        # if it is a directory or a file:
        if method == 'no_copy':
            return
        if self.excludedByPattern():
            return
        if self.preservedByPattern():
            cmd = shutil.copy2
        elif method == 'link':
            cmd = os.symlink
        elif method == 'copy':
            cmd = shutil.copy2
        else:
            DARInternalError("in  smartCopy: no method "+method)
        if os.path.exists(dest):
            return
        # Do not link if it is a directory:
        if self.isdir():
            if not os.path.exists(dest):
                os.makedirs(dest)
        elif self.isfile():
            dirname = os.path.dirname(dest)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            # Issue a warning in case of  copy failure
            # e.g. for  unreadable files 
            try:
                cmd(self.path, dest)
            except IOError, myException:
                warning('failed to copy' + self.path + ' to ' + \
                        dest + " : "+ \
                        myException.args[1])
        else:
            print "Problem copying entry: ", self.path, 'to', \
                  dest, 'using method', method
            DARInternalError("in  smartCopy: not a file and not a directory.")

class FSO(Lister):
    """
    class FSO:
      Represents a file system object as a collection of Entry objects
    """
    def __init__(self, fsoPath, bunchArg):
        Lister.__init__(self)
        self.arg = bunchArg
        self.path = fsoPath
        if not _ValidPath(fsoPath):
            raise InvalidPath(strong('ERROR:')+'  invalid path: ' + fsoPath)
        self.entries = {}
        self.commonpath = '/'
        
        if os.path.isfile(fsoPath):
            self._FsoFromFile(fsoPath)
        if os.path.isdir(fsoPath):
            infoOut( 'Create fso from dir: '+fsoPath)
            self._FsoFromDir(fsoPath)

    def createEntry(self, dirname, files):
        """
        FSO.createEntry:
          Creates entries in the entries dictionary from a list
          of given file names
        """
        for fName in files:
            filename = os.path.join(dirname, fName)
            self.entries[filename] = Entry(filename, self.arg)

        
    def _RealPath(self, fsoPath):
        """
        Returns canonical path: eliminates any intermediate symbolic links
        """
        return os.path.realpath(fsoPath)

    def makeCommonPath(self):
        """
        FSO.makeCommonPath:
        """
        self.commonpath = None

        for fsoPath, entry in self.entries.items():
            if entry.isfile():
                fsoPath = os.path.dirname(fsoPath)
            elif entry.isdir():
                pass
            else:
                continue
            if self.commonpath:
                self.commonpath = commonPath(self.commonpath, fsoPath)
            else:
                self.commonpath = fsoPath

    def mergeFso (self, fso):
        """
        Merges an FSO object with the current one.
        If we are empty, just make ourself equal to the passed in object
        Otherwise, we populate our list of entries with the given object's values
        """
        if self == None:
            self = fso
            return
        if fso:
            for k in fso.entries.keys ():
                self.entries[k] = fso.entries[k]
            self.makeCommonPath()

    def _FsoFromFile(self, fsoPath):
        """
        FSO._FsoFromFile:
          Initializes an fso object if path is a file
        """            
        self.entries[fsoPath] = Entry(fsoPath, self.arg)
        self.commonpath = canonicalPath(os.path.dirname(fsoPath))

    # def _FsoFromDir(self, fsoPath, subdirs="yes"):
    def _FsoFromDir(self, fsoPath):
        """
        Initializes an fso object if path is a directory
        By default subdirectories are included recursively.
        If called with subdirs equal to no, no subdirectories is included.
        """
        # Take only directories with absolute path:
        if os.path.isabs(fsoPath):
            os.path.walk(fsoPath, FSO.createEntry, self)
            #   print "FSO::FsoFromDir-> fsoPath:",
            #                         fsoPath," entries:", self.entries
            self.makeCommonPath()
        else:
            warning(' no entries created for relative path '+fsoPath)
                
    def moveEntry(self, entry, dest, method='copy' ):
        """
        FSO.moveEntry:
          Copies entry to destination and returns a new entry
        """
        if entry.type == 'stat_failed':
            return
        if self.entries.has_key(entry.path):
            entry.smartCopy(dest, method)            
            self.path = dest

    def copyContent (self, sharedDir, rteDirectory, baseDir='', 
                     baseBom = {}, method='copy'):
        """
        Copies fso object's entries in two steps.
        First creates and so-called fso image, using specified  method,
        then creates symbolic links from the rteDir area pointing to
        the image of the entry. 
        """
        for fsoPath, entry in self.entries.items():
            # Do not do anything if stat failed for this entry:
            if entry.type == 'stat_failed':
                warning('stat failed for this entry. Do not copy '+fsoPath)
                continue
            # Do not do anything  if entry is excluded:
            if entry.excludedByPattern():
                warning('excluded file '+fsoPath)
                continue
            if entry.foundInBase(baseBom):
                dest = baseDir+fsoPath
                self.moveEntry(entry, dest, method='no_copy')
            else:
                # Create global fso images:
                dest = sharedDir+fsoPath
                self.moveEntry(entry, dest, method)
            if entry.isdir():
                pathname = fsoPath
                filename = None
            elif entry.isfile():
                pathname = os.path.dirname(fsoPath)
                filename = os.path.basename(fsoPath)
            else:
                print "FSO.copyContent: skip undefined path %s" % fsoPath
                continue
            # Create a symlink from the rteDir:
            rteToDir = canonicalPath("%s/%s"%(rteDirectory, \
                                              stripPath(pathname, \
                                                        self.commonpath)))
            if not os.path.exists(rteToDir):
                os.makedirs(rteToDir)
            if entry.isdir():
                if not os.path.exists(pathname):
                    os.makedirs(pathname)
            elif entry.isfile():
                if entry.preservedByPattern():                    
                    # Issue a warning  in case of copy failure
                    # e.g. for unreadable  files.
                    try:
                        shutil.copy2 (dest, os.path.join(rteToDir, filename))
                    except IOError, myException:
                        warning('failed to copy' + dest + ' to ' + \
                                os.path.join(rteToDir, filename) + " : "+ \
                                myException.args[1])
                else:
                    link = shortcut(rteToDir, os.path.dirname(dest))
                    os.symlink(os.path.join(link, filename), \
                               os.path.join(rteToDir, filename))

###################################
#  Module tests:
###################################

if __name__ == '__main__':
    # Create temporary directory structure on the flight:
    tmpDir = "/tmp/fsoTestTmpDir_"+str(os.getpid())
    os.makedirs(tmpDir)
    acopy = tmpDir+'/fso_image'
    os.mkdir(acopy)
    rteDir = tmpDir+'/rte_Structure'
    os.mkdir(rteDir)
    print strong("\n   ********    TEST # 2 ( "+ \
                 "preserve/exclude/alwaysKeep lists)*******  \n\n")
    excludeList =          ['*.pyc', 'CVS']
    preserveList =         ['F*.py~']
    alwaysKeepList =   [ '*/R*']
    arg1 = Bunch(excludeList = convertPatternList(excludeList),
              preserveList = convertPatternList(preserveList),
              alwaysKeepList = convertPatternList(alwaysKeepList)
              )
    print arg1
    #path = '/home/natasha/WORK/DAR-2/head/src/modules'
    path = '/home/natasha/WORK/DAR-2/DAR-DEV/doc'
    fso1 = createFSO(path, arg1)
    excludeList =           ['*~']
    preserveList =          []
    alwaysKeepList =   []
    arg2 = Bunch(excludeList = convertPatternList(excludeList),
              preserveList = convertPatternList(preserveList),
              alwaysKeepList = convertPatternList(alwaysKeepList)
              )
    print arg2
    fso2 = createFSO(path, arg2) # same path
    fso1.mergeFso(fso2)
    fso1.copyContent( acopy, rteDir, method='copy')
