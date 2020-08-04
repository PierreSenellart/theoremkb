from typing import List, Tuple

class Layer:
    name: str
    parents: List[Tuple[str, List[str]]]
    labels: List[str]

class SegmentationLayer(Layer):
    name   = "segmentation"
    labels = ["titlePage", "front", "headnote", "footnote", "body", "listBibl", "page", "annex"]
    parents= []

class HeaderLayer(Layer):
    name   = "header"
    labels = ["title"]
    parents= [("segmentation", ["front"])]

class ResultsLayer(Layer):
    name   = "results"
    labels = ["theorem", "definition", "lemma", "proof"]
    parents= [("segmentation", ["body"])]
