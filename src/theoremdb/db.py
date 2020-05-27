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

        main_source_path = f"{WORKING_PATH}/{paper}/{paper}.tex"

        if os.path.exists(main_source_path):
            re_class = re.compile(rb"^\s*\\documentclass\s*(\[.*?\])?\s*\{(.*?)\}", re.M|re.S)
            with open(main_source_path, 'rb') as source_tex:
                content = source_tex.read()
                result  = re_class.search(content)

                if result is None:
                    print(content)
                    print(f"Failed to get document class for {paper}")
                    self.dclass = "unk"
                    exit(0)
                else:
                    self.dclass = result.group(2).decode('unicode_escape')
                    if "%" in self.dclass: # workaround, paper 1210.2459 has a 
                                           # comment inside the document class.
                        self.dclass = self.dclass.replace("%","").strip()
                        print(paper)
                    #print(self.dclass)
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
