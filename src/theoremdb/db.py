import re,os,sys,pickle
from collections import namedtuple
from tqdm import tqdm
from joblib import Parallel, delayed  
from lxml import etree as ET

from ..config import TARGET_PATH, WORKING_PATH, DATA_PATH, ensuredir
from .results import ResultsBoundingBoxes
 
class Paper:
    def __init__(self, paper):
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
            results      = ResultsBoundingBoxes(xml_annot)
 
            self.results = results
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
    def __init__(self):
        def process_paper(paper):
            #print(paper, "=> ", end="")
            return Paper(paper)
        
        papers = [process_paper(dir) for dir in tqdm(list(os.listdir(TARGET_PATH)))]
    
        self.papers = {}
        for paper in papers:
            self.papers[paper.id] = paper
        
        print("Read", len(self.papers), "papers.")
