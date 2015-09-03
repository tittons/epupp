#!/usr/local/bin/python3

"""
epuppies contains different utilities for the main module
"""

import errno
import os
import re
import sys
import traceback
import zipfile
from lxml import etree, html

def handle_error(e):
    exc_type, exc_value, exc_traceback = sys.exc_info()
    traceback.print_exception(exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)
    print()
    
def make_dir(directory):
    """
    Tries to create a directory if it doesn't exist.
    
    Args:
        directory (str): A name of a directory to check
    """
    try:
        os.makedirs(directory,mode=0o775)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
            
                
def find_file(archive,filename):
    """
    Tries to find and return a filename from epub.
    
    Args:
        new_filename (str): a name of a file we need to check for existence.
    Returns:
        None: if the file doesn't exist, else 'filename'.
    """
    new_filename = filename
    try:
        archive.read(new_filename)
    except:
        try:
            new_filename = "OPS/%s" % filename
            archive.read(new_filename)
        except:
            try:
                new_filename = "OEBPS/%s" % filename
                archive.read(new_filename)
            except:
                pass
    return new_filename
    

def build_chapter(file,element="section"):
    """
    Parses html or xml documents in epub and extracts data from them into a specified element.
    
    Args:
        file (ZipExtFile): a file to read the text from.
        element (Optional[str]): optional name of a tag to write the parsed text into. Defaults to 'section'.
    Returns:
        root (lxml.etree.Element): Root element containing text of the book formatted as html.
    Raises:
        AttributeError: if match in rewrite_links() is not found.
        TypeError: if 'file' is not a ZipExtFile instance.
    """
    root = etree.Element(element)
    
    try:
        #gets the file's body
        body = html.fromstring(
            b''.join(file.readlines())
        ).body
        
        #enumerates parapgraphs
        ps = body.cssselect("p")
        for i,p in enumerate(ps):
            p.attrib["data-pid"]=str(i)
        
        #collects data from body
        ps = body.cssselect("body>*")
    
        #deletes original file names from hash links
        def rewrite_links(link):
            match = re.compile(r'\S+(#\S+)').match(link)
            return match.group(1) if match else link

        #appends all paragraphs from the file to the new root
        for p in ps:
            p.rewrite_links(rewrite_links)
            root.append(p)
            
    except (AttributeError, TypeError) as e:
        handle_error(e)
    
    return root