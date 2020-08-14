from dataclasses import dataclass
from os import name
from typing import List, Tuple

@dataclass
class LayerParent:
    name: str
    tags: List[str]

    def to_web(self):
        return {"name": self.name, "tags": self.tags}

class Layer:
    name: str
    parents: List[LayerParent]
    labels: List[str]

class SegmentationLayer(Layer):
    name   = "segmentation"
    labels = ["titlePage", "front", "headnote", "footnote", "body", "listBibl", "page", "annex"]
    parents= []

class HeaderLayer(Layer):
    name   = "header"
    labels = ["title"]
    parents= [LayerParent("segmentation", ["front"])]

class ResultsLayer(Layer):
    name   = "results"
    labels = ["theorem", "definition", "lemma", "proof"]
    parents= [LayerParent("segmentation", ["body"])]
