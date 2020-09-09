from dataclasses import dataclass
from typing import List

"""
Annotation classes. 
"""


@dataclass
class AnnotationClassFilter:
    """
    A class filter defines a subset of labels from a given class.
    """

    name: str
    labels: List[str]

    def to_web(self):
        return {"name": self.name, "labels": self.labels}


class AnnotationClass:
    """
    An annotation class is a set of possible labels.
    It can also specify parent classes in which this class
    can exist. 
    """

    name: str
    parents: List[AnnotationClassFilter]
    labels: List[str]

class MiscAnnotationClass(AnnotationClass):
    name    = "misc"
    labels  = []
    parents = []

class SegmentationAnnotationClass(AnnotationClass):
    """
    Segmentation is the first class, coarsely separating the document.
    """

    name = "segmentation"
    labels = [
        "acknowledgement",
        "front",
        "headnote",
        "footnote",
        "body",
        "bibliography",
        "page",
        "annex",
    ]
    parents = []

class HeaderAnnotationClass(AnnotationClass):
    """
    Header information, living in the segmentation/front part of the document.
    """

    name = "header"
    labels = ["title"]
    parents = [AnnotationClassFilter("segmentation", ["front"])]


class ResultsAnnotationClass(AnnotationClass):
    """
    Theoretical results in a maths/computer science paper.
    """

    name = "results"
    labels = ["lemma", "theorem", "proposition", "definition", "remark", "corollary", "claim", "conjecture", "assumption", "proof"]
    parents = [AnnotationClassFilter("segmentation", ["body","annex"])]


ALL_CLASSES = [
    SegmentationAnnotationClass(),
    HeaderAnnotationClass(),
    ResultsAnnotationClass(),
    MiscAnnotationClass(),
]
