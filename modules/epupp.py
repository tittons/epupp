#!/usr/local/bin/python3

"""
Epub Parser for Python or simply 'epupp' is a module containg class EpuPP (with helpers module), which provides tools for parsing
epub-documents, extracting information from them into 3 entities: info, images, chapters, 
and writing these entities into files if needed
""" 

import json
import zipfile
from .helpers import build_chapter, find_file, handle_error, make_dir
from lxml import etree, html
from lxml.html.clean import Cleaner

class EpuPP(object):
    """
    A class with methods to extract data from epub archives
    
    Attributes:
        ns (dict): Dictionary of epub-specific namespaces
        ifile (str): Name of a file to extract content of the book from
        ofile (str): Name of a file to extract main content of the book (excluding all meta information and images) into
        base_path (str): Base directory to store files into
        epub_info (dict): Dictionary of the book meta information, such as
            title, language, creator, date, identifier, description, 
            book (name of an output file where chapters were put),
            book_dir, cover (path to, after extraction), images (path to, after extraction), genres.
        remove_original (bool): If it should remove the original file on __exit__().
        original: Path to the original file.
    """
    def __init__(self,input_file,output_file="output.html",base_path="./", remove_original=False):
        """
        Init method.
        
        Args:
            ifname (str): Input file name.
            ofname (str): Ouput file name.
            base_path (Optional[str]): Path to the base directory.
        Raises:
            FileNotFoundError: if a file with a name specified by 'ifname' doesn't exist
        """
        self.ns = {
            'n':'urn:oasis:names:tc:opendocument:xmlns:container',
            'pkg':'http://www.idpf.org/2007/opf',
            'dc':'http://purl.org/dc/elements/1.1/',
            'atom':'http://www.w3.org/2005/Atom',
            'ncx':'http://www.daisy.org/z3986/2005/ncx/'
        }
        self.ofile = output_file
        self.epub_info = {}
        self.base_path = base_path
        try:
            self.ifile = zipfile.ZipFile(input_file)
            self.original = input_file
        except FileNotFoundError as e:
            handle_error(e)
            self.ifile = ""
            self.original = ""
        self.remove_original = remove_original
            
    def __enter__(self):
        return self
        
    def __exit__(self,exc_type, exc_value, traceback):
        try:
            self.ifile.close()
            if self.remove_original:
                import os
                os.remove(self.original)
        except:
            pass

    def get_epub_info(self):
        """
        Extracts important epub info into a dictionary.
        
        Returns:
            self.epub_info (dict): Dictionary with basic information ebout epub:
                title, language, creator, date, identifier, description.
            None: if input file is not found.
        Raises:
            IndexError: if pkg:metadata or some of the attributes is not found
        """
        if not self.ifile: return
        
        if not self.epub_info:

            try:
                # grabs the metadata block from the contents metafile
                p = self.__get_cftree().xpath('/pkg:package/pkg:metadata',namespaces=self.ns)[0]
            except IndexError as e:
                handle_error(e)
                p = etree.Element("metadata")

            # repackages the data
            for s in ['title','language','creator','date','identifier','description']:
                try:
                    self.epub_info[s] = p.xpath('dc:%s/text()'%(s),namespaces=self.ns)[0]
                except IndexError as e:
                    handle_error(e)
                    self.epub_info[s] = ""

            self.epub_info['genres'] = self.__get_genres()
            self.epub_info['table_of_contents'] = self.__get_table_of_contents()
        return self.epub_info

    def extract_images(self):
        """
        Extracts images from epub into a folder called 'images' within the base_path 
        extended by a path to the unpacked book folder, and returns a full path to the images.
        Sets the value of self.epub_info['images'] to be equal to the full path to the images.
        
        Returns:
            self.epub_info["images"] (str): Path to a directory where the images were (supposedly) put
            None: if input file is not found, or self.__get_book_dir() returns None.
        """
        if not self.ifile or not self.__get_book_dir() : return
        files = self.__get_files()
        self.epub_info["images"] = "%s/%s/" % (self.__get_book_dir(), "images")
        make_dir(self.epub_info["images"])
        for filename in files:
            if "images" in filename:
                original = find_file(self.ifile,filename)
                try:
                    with self.ifile.open(original) as ifile:
                        data = ifile.read()
                        path = "%s/%s"%(self.__get_book_dir(),filename)
                        with open(path,"wb") as ofile:
                            ofile.write(data)
                            if "cover" in filename:
                                self.__set_path_to_cover(path)
                except KeyError as e:
                    handle_error(e)
        return self.epub_info["images"]

    def get_chapters(self, extract_images=True, images_path=None, as_list=False, clean=True, cleaner_params={}):
        """
        Extracts content of all files from epub into a single string and returns it.
        
        Args:
            extract_images (bool): If it should extract images from epub. Defaults to True.
            images_path (str): A path where all images src's should lead to. 
                If not set, uses self.epub_info["images"], which should be set by self.extract_images() if extract_images = False.
                If self.epub_info["images"] is not set, uses "images/".
            as_list (bool): Return chapters as a list or as an HTML-string. Defaults to False.
            clean (bool): If chapters should be cleaned off of malicious HTML.
            cleaner_params (dict): Dictionary of cleaner params, 
                a full list of which is available in the documentation to lxml.html.clean.Cleaner class.
        Returns:
            chapters (str|list): String or list of strings containing the text of the book formatted as html.
            None: if input file is not found.
        Raises:
            KeyError: if a file is not found in the epub archive.
        """
        if not self.ifile: return
            
        #set paths to images in chapters' markup
        epub_images = self.get_epub_info().get("images")
        if images_path:
            images_path =  images_path
        else:
            if epub_images:
                images_path = epub_images
            else:
                images_path = "images/"
                
        #extract images
        if extract_images:
            self.extract_images()

        files = self.__get_files()
        
        #create a cleaner
        cleaner = Cleaner(**cleaner_params) if clean else None
        
        if as_list:
            chapters = []
            for filename in files:
                if ".htm" in filename or ".xml" in filename:
                    original = find_file(self.ifile,filename)
                    try:
                        with self.ifile.open(original) as f:
                            chapter = build_chapter(f, images_path=images_path, cleaner=cleaner)
                            chapter.attrib["id"]=filename
                            chapters.append(html.tostring(chapter).decode('utf-8'))
                    except KeyError as e:
                        handle_error(e)
        else:
            chapters = etree.Element("div")
            for filename in files:
                if ".htm" in filename or ".xml" in filename:
                    original = find_file(self.ifile,filename)
                    try:
                        with self.ifile.open(original) as f:
                            chapter = build_chapter(f, images_path=images_path, cleaner=cleaner)
                            chapter.attrib["id"]=filename
                            chapters.append(chapter)
                    except KeyError as e:
                        handle_error(e)
            chapters = html.tostring(chapters).decode('utf-8')
        return chapters

    def write_to_file(self,res, optional_filename=""):
        """
        Writes a text array or dictionary into a specified file and returns the path to it.
        
        Args:
            res: a resource to write into a file.
            optional_filename (Optional[str]): a name of a file we're going to write into. 
                 If not specified uses self.ofile.
        Returns:
            path (str): a path to a file we are writing into.
            None: if input or output file is not found, or self.__get_book_dir() returns None.
        Raises: 
            FileNotFoundError: if self.__get_book_dir() returns None
        """
        file = optional_filename if optional_filename else self.ofile
        if not self.ifile or not file or not self.__get_book_dir() : return
        
        if ".js" in file:
            res = json.dumps(res, sort_keys=True, indent=4)
        else:
            res = str(res)
            
        path = "%s/%s"%(self.__get_book_dir(),file)
        try:
            with open(path,"w") as f:
                if file == self.ofile:
                    self.epub_info['book']=path
                f.write(res)
        except FileNotFoundError as e:
            handle_error(e)
            
        return path

    def __get_cftree(self):
        """
        Finds a contents metafile.
        
        Returns:
            cftree (lxlml.etree.Element): An xml-tree of a metafile
        Raises:
            KeyError: if the metafile is not found
            IndexError: if @full-path is not found in the metafile
        """
        cftree = etree.Element("package")
        try:
            cfname = etree.fromstring(
                self.ifile.read('META-INF/container.xml')
            ).xpath(
                'n:rootfiles/n:rootfile/@full-path',namespaces=self.ns
            )[0]
            cftree = etree.fromstring(self.ifile.read(cfname))
        except (KeyError,IndexError) as e:
            handle_error(e)
        return cftree

    def __get_book_dir(self):
        """
        Makes a directory for a book files and returns a path to it.
        
        Returns:
            self.epub_info['book_dir'] (str): A path to a directory of the unpacked epub.
        Raises:
            KeyError: if self.epub_info is empty.
        """
        if not 'book_dir' in self.epub_info:
            try:
                info = self.get_epub_info()
                directory = "%s/%s/%s" % (self.base_path.rstrip("/"), info['title'], info['identifier'])
                make_dir(directory)
                self.epub_info['book_dir'] = directory
            except KeyError as e:
                handle_error(e)
                self.epub_info['book_dir'] = None
        return self.epub_info['book_dir']
    
    def __get_files(self):
        """
        Collects href attributes of all items.
        
        Returns:
            files (list): of the attributes
        Raises:
            IndexError: if pkg:manifest is not found
        """
        files = []
        try:
            files = self.__get_cftree().xpath(
                '/pkg:package/pkg:manifest',namespaces=self.ns
            )[0].xpath(
                'pkg:item/@href', namespaces=self.ns
            )
        except IndexError as e:
            handle_error(e)
        return files
        
    def __get_genres(self):
        """
        Collects genres of the book.
        
        Returns:
            self.epub_info['genres'] (list): of genres
        Raises:
            KeyError: if metadata.xml is not found
        """
        genres = []
        if 'genres' in self.epub_info: return self.epub_info['genres']
        try:
            genres = etree.fromstring(
                self.ifile.read('META-INF/metadata.xml')
            ).xpath(
                'atom:category/@label',namespaces=self.ns
            )
        except KeyError as e:
            handle_error(e)
        return genres
            
    def __get_table_of_contents(self):
        """
        Finds a navigational file.
    
        Returns:
            toc (dict): A Dictionary with a table of contents of a file. 
                Dict keys: 'title' (str), 'author' (str), 'navpoints' (list).
                'navpoints' contains Dictionaries with keys: 'raw_id' (str), 'text' (str), 'done_id' (str), for each navPoint.
        """
        if 'table_of_contents' in self.epub_info: return self.epub_info['table_of_contents']
        toc = {
            'title':None,
            'author':None,
            'navpoints':[]
        }
        for filename in self.ifile.namelist():
            if ".ncx" in filename:
                try:
                    tree = etree.fromstring(
                        self.ifile.read(filename)
                    )
                    toc['title'] = tree.xpath('ncx:docTitle/ncx:text/text()',namespaces=self.ns)[0]
                    toc['author'] = tree.xpath('ncx:docAuthor/ncx:text/text()',namespaces=self.ns)[0]
                    navpoints = tree.xpath('ncx:navMap/ncx:navPoint',namespaces=self.ns)
                    for np in navpoints:
                        try:
                            point = {
                                'raw_id': np.xpath('@id',namespaces=self.ns)[0],
                                'text': np.xpath('ncx:navLabel/ncx:text/text()',namespaces=self.ns)[0],
                                'done_id': np.xpath('ncx:content/@src',namespaces=self.ns)[0],
                            }
                        except:
                            pass
                        else:
                            toc['navpoints'].append(point)
                except (KeyError,IndexError) as e:
                    handle_error(e)
        return toc
    
    def __set_path_to_cover(self,path):
        """
        Puts a path to the cover of epub into self.epub_info.
        
        Args:
            path (str): a path to a cover of the book
        Returns:
            None: if the path is 'falsy', else 'path'.
        """
        if not path: 
            return
        else:
            self.epub_info['cover']=path
            return path