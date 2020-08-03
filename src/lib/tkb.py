from __future__ import annotations
from typing import Dict, List, Optional
import jsonpickle

from .config import DATA_PATH
from .layers import HeaderLayer, Layer, ResultsLayer, SegmentationLayer
from .paper import Paper
from .extractors import Extractor
from .extractors.segmentation import SegmentationCRFExtractor
from .extractors.results import ResultsLatexExtractor

class TheoremKB:

    prefix: str
    papers: Dict[str, Paper]
    layers: Dict[str, Layer]
    extractors: Dict[str, Extractor]

    def __init__(self, prefix=DATA_PATH) -> None:
        self.prefix = prefix

        try:
            with open(f"{prefix}/tkb.json", "r") as f:
                self.papers = jsonpickle.decode(f.read())
        except Exception as e:
            print("Loading failed:", str(e))
            self.papers = {}
 
        self.layers = {}
        for l in [SegmentationLayer(),HeaderLayer(),ResultsLayer()]:
            self.layers[l.name] = l

        self.extractors = {}
        for e in [SegmentationCRFExtractor(prefix),ResultsLatexExtractor()]:
            self.extractors[f"{e.kind}.{e.name}"] = e
    
    def save(self):
        with open(f"{self.prefix}/tkb.json", "w") as f:
            f.write(jsonpickle.encode(self.papers))


    def get_paper(self, id) -> Paper:
        if id in self.papers:
            return self.papers[id]
        else:
            raise Exception("Paper not found.")

    def list_papers(self) -> List[Paper]:
        return list(self.papers.values())

    def add_paper(self, id: str, pdf_path: str):
        paper = Paper(id, pdf_path)
        self.papers[id] = paper
