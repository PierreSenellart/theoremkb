"""
## Annotation classes

Annotation classes define the possible set of labels for each kind of annotation layer.
It can also define a constraint to define in which subset of a document which annotation can live.
(for example, the header annotation class lives in the header section of the segmentation annotation class)

The available annotation classes are:

* `SegmentationAnnotationClass`
* `HeaderAnnotationClass`
* `ResultsAnnotationClass`
* `MiscAnnotationClass`
"""

from dataclasses import dataclass
from typing import List


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
    """
    Class name
    """
    parents: List[AnnotationClassFilter]
    """
    In which classes this class can exist. 
    """
    labels: List[str]
    """
    Possible labels for this class.
    """


class MiscAnnotationClass:
    """
    Miscellanous class that doesn't hold any label.
    """

    name = "misc"
    labels = []
    parents = []


class SegmentationAnnotationClass:
    """
    Segmentation coarsely separates the document.
    """

    name = "segmentation"
    """
    `segmentation`
    """
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
    """
    `acknowledgement`,`front`,`headnote`,`footnote`,`body`,`bibliography`,`page`,`annex`
    """
    parents = []
    """
    `[]`
    """


class HeaderAnnotationClass:
    """
    Header information, living in the segmentation/front part of the document.
    """

    name = "header"
    """
    `header`
    """
    labels = ["title"]
    """
    [`title`]
    """
    parents = [AnnotationClassFilter("segmentation", ["front"])]
    """
    [`segmentation.front`]
    """


class ResultsAnnotationClass:
    """
    Theoretical results in a maths/computer science paper.
    """

    name = "results"
    """
    `results`
    """
    labels = [
        "lemma",
        "theorem",
        "proposition",
        "definition",
        "remark",
        "corollary",
        "claim",
        "conjecture",
        "assumption",
        "proof",
    ]
    """
    `lemma`,`theorem`,`proposition`,`definition`,`remark`,`corollary`,`claim`,`conjecture`,`assumption`,`proof`
    """
    parents = [AnnotationClassFilter("segmentation", ["body", "annex"])]
    """
    [`segmentation.body`,`segmentation.annex`]
    """


ALL_CLASSES = [
    SegmentationAnnotationClass(),
    HeaderAnnotationClass(),
    ResultsAnnotationClass(),
    MiscAnnotationClass(),
]
