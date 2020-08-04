import re,os,sys,pickle
from collections import namedtuple
from tqdm import tqdm
from joblib import Parallel, delayed  
from lxml import etree as ET
import pandas as pd

from ..config import TARGET_PATH, WORKING_PATH, LINKS_PATH, ensuredir
from .results import ResultsBoundingBoxes
from .links import RefsBBX
 

def loadLinks(verbose=False,max_file=100):
	dico = {}
	last_seen = ""
	for i in range(max_file):
		if verbose:
			print("Loading %i..."%i)
		df = pd.read_csv(LINKS_PATH+"/links_%i.csv"%i,index_col=0,dtype=str)
		for _,row in df.iterrows():
			if row.pdf_from != last_seen:
				dico[row.pdf_from] = {}
				last_seen = row.pdf_from
			dico[row.pdf_from][row.tag] = row.pdf_to

	return dico

class Paper:
    def __init__(self, paper,merge_all=True):
        self.id = paper

        source_path = f"{WORKING_PATH}/{paper}/"

        if os.path.exists(source_path):
            re_class = re.compile(rb"^\s*\\(documentclass|documentstyle)\s*(\[.*?\])?\s*\{(.*?)\}", re.M|re.S)
            found_class = "unk"

            for file in filter(lambda x: ".tex" in x, os.listdir(source_path)):
                with open(source_path+file, 'rb') as source_tex:
                    content = source_tex.read()
                    result  = re_class.search(content)
                    
                    if result is not None:
                        found_class = result.group(3).decode('unicode_escape')
                        if "%" in found_class: # workaround, paper 1210.2459 has a 
                                            # comment inside the document class.
                            found_class = found_class.replace("%","").strip()
                            print(paper)
                        #print(self.dclass)
                        break

            if found_class == "unk": 
                print(f"Failed to get document class for {paper}")
            
            self.dclass = found_class
        else:
            #print("no src")
            self.dclass = "no_src"

        parser    = ET.XMLParser(recover=True)
        if os.path.exists(f"{TARGET_PATH}/{paper}/{paper}.xml"):
            xml_annot    = ET.parse(f"{TARGET_PATH}/{paper}/{paper}_annot.xml", parser=parser)
            results      = ResultsBoundingBoxes(xml_annot,merge_all=merge_all)
            
            refs         = RefsBBX(xml_annot) 
 
            self.results = results
            self.refs    = refs
            self.status  = "OK"
        else: 
            self.results = None
            self.status  = "No XML"

    def describe(self):
        print(f"Paper {self.id}")

        if self.dclass == "no_src":
            print("No source.")
            return
        
        print("Document class:", self.dclass)
        print("Theorem extraction:", self.status)
        if self.results is not None:
            for kind, data in self.results._data.items():
                print(f"[{kind}] {len(data)}: {list(data.keys())}")
    
    def n_results(self):
        if self.results is not None:
            return sum([len(x) for x in self.results._data.values()])
        else:
            return 0





class TheoremDB:
    def __init__(self,n=1000000000,list_paper=None,merge_all=True,subfolder=None):
        if subfolder != None:
            TARGET_PATH += '/' + subfolder
            WORKING_PATH += '/' + subfolder
        
        def process_paper(paper):
            #print(paper, "=> ", end="")
            return Paper(paper)
        
        if list_paper== None:
            papers = [process_paper(dir) for dir in tqdm(list(os.listdir(TARGET_PATH)[:n]))]
        else:
            papers = [process_paper(p) for p in tqdm(list_paper)]
        self.papers = {}
        
        for paper in papers:
            self.papers[paper.id] = paper
        
        print("Read", len(self.papers), "papers.")
