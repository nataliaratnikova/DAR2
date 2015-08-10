
import os
class ReleaseNotes:
    #This class generates an html page with relese notes for the software installation
    def __init__(self, darfilename, release_date):
        self.darfilename=darfilename
       
        #self.sourcefile=content_html # This path should be submitted from configurstion file
        self.release_date=release_date
        
        #self.source=open(self.sourcefile,'r')
        self.structure={}
        self.rev_structure={}
        self.curr_idx=0
        self.buffer=[]

    def default_structure(self): # Defines default structure for the release notes document
        self.structure= {'Aviability':0,'Content':1,'Installation instructions':2,'Verify installation tests':3,'Noticed problems and bugs':4}
        self.buffer=[[],[],[],[],[]]
        self.curr_idx=5

    def add_section(self,section_name): # Defines new section in the document
                                        # Returns 1 is successful
                                        # Returns 0 in case of the error
        if self.structure.has_key(section_name):
            return 0
        else:
            self.structure[section_name]=self.curr_idx
            self.buffer.append([])
            self.curr_idx=self.curr_idx+1
            return 1
    
    def push_tosection(self,section_name,content): # Adds record to the appropriate section of the document
                                                 # Returns 1 is successful
                                                 # Returns 0 in case of the error
        if self.structure.has_key(section_name):
            self.buffer[self.structure[section_name]].append(content)
            return 1
        else:
            return 0

    def publish_document(self,release_html): # Creates an html release notes document
                                # Must be used after config method was started
        #Revircing the dictionary
        self.target=open(release_html,'w')
        for x in self.structure.keys():
            self.rev_structure[self.structure[x]]=x
        
        self.target.write("<!DOCTYPE HTML PUBLIC \"-//IETF//DTD HTML//EN\">\n<html>\n")
        self.target.write("<head><title>Software distribution</title></head>\n")
        self.target.write("<body BGCOLOR=#c0c0c0 TEXT=#000000 alink=#339933 link=#336699>\n")

        # Page title goes here
        self.target.write("<h1>"+self.darfilename+"\n<br>\n")
        self.target.write("<font size=-1> created on "+self.release_date+"</h1>\n")

        keys=self.structure.keys()
        
        #Creating structural menu
        for i in range(len(self.structure)):
            pass
            self.target.write("<IMG SRC=\"GIF/whitebal.gif\"> <a href=\"#anch"+str(i)+"\">"+self.rev_structure[i]+"</a>\n<br>\n")
        self.target.write("<hr>\n")
        
        #Printing each section
        for i in range(len(self.structure)):
            self.target.write("<a name=\"anch"+str(i)+"\"><u><b>"+self.rev_structure[i]+"</b></u><br>\n")
            self.target.writelines(self.buffer[i])
            self.target.write("<hr>\n")

        #Finishing html document
        self.target.write("<P>Please send your comments and bug reports to <address>")
        self.target.write("<a href=\"mailto:natasha@fnal.gov\">Natalia Ratnikova</a></address>\n")
        self.target.write("</body></html>\n")
        self.target.write("<font size=-1><script language=\"JavaScript\">\n")
        self.target.write("<!-- hide document.write('Document last modified: ', document.lastModified)\n")
        self.target.write("// --></script></font>\n")
        self.target.close()

        # Adding a link to the releases menu
        #buff=self.source.readline()
        #flag=0
        #content_buff=[]
        #while buff !="":
        #    content_buff.append(buff)
        #    if buff == "<h3>available items:</h3>\n":
        #        content_buff.append("<a href=\""+self.targetfile+"\"><nobr>"+self.darfilename+"</nobr></a> <br>\n")
        #        flag=1
        #    buff=self.source.readline()
        #self.source.close()
        #self.source=open(self.sourcefile,'w')
        #self.source.writelines(content_buff)
        #self.source.close()
          
        #end of class

if __name__ == '__main__':
    print "tests to  be added " 
    a=ReleaseNotes("target.html","templates/content.html","Test","07/02/2003")
    a.default_structure()
    a.add_section("G")
    a.add_section('Aviability')
    a.push_tosection('Aviability',"The life is great!<br>")
    a.push_tosection('Aviability',"Bla-bla-blah")
    a.push_tosection('G',"Bla-bla-blah")
    a.publish_document()


