from typing import List, Tuple
from lxml import etree as ET

from ..paper import AnnotationLayer
from ..misc.bounding_box import BBX

class Layer:
    name: str
    parents: List[Tuple[str, str]]
    labels: List[str]

class SegmentationLayer(Layer):
    def __init__(self):
        self.name   = "segmentation"
        self.labels = ["titlePage", "front", "headnote", "footnote", "body", "listBibl", "page", "annex"]
        self.parents= []

class HeaderLayer(Layer):
    def __init__(self):
        self.name   = "header"
        self.labels = ["title"]
        self.parents= [("segmentation", "front")]

class ResultsLayer(Layer):
    def __init__(self):
        self.name   = "results"
        self.labels = ["theorem", "definition", "lemma", "proof"]
        self.parents= [("segmentation", "body")]
