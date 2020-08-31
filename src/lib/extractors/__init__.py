from abc import abstractmethod
from typing import List, Tuple
import argparse

from ..annotations import AnnotationLayer
from ..classes import AnnotationClass
from ..paper import AnnotationLayerInfo, Paper
from ..misc.namespaces import *

"""
An extractor takes a paper as an input, optionally with several annotations layers of class specified by the requirements property. 
It outputs an annotation layer that can be displayed and/or saved.
The extractor might be trainable, for example when machine learning models are used.
"""


class Extractor:
    """Abstract class for an annotation layer builder"""

    @property
    @classmethod
    def name(self) -> str:
        """Extractor name"""

    @property
    @classmethod
    def class_(self) -> AnnotationClass:
        """Which class of annotations it extracts"""

    @abstractmethod
    def apply(self, document: Paper) -> AnnotationLayer:
        """Create an annotation layer from the given article.

        ## Args:

        **document** (`lib.paper.Paper`): the article to annotate.

        **requirements** (`Dict[str, lib.annotations.AnnotationLayer`]): additional layers required for extraction.

        ## Returns: `lib.annotations.AnnotationLayer`
        """

    def apply_and_save(self, document: Paper, name: str) -> AnnotationLayer:

        annotations = self.apply(document)
        annotations = annotations.reduce()
        annotations.filter(lambda x: x.label != "O")

        return document.add_annotation_layer(name, self.class_.name, False, content=annotations)


class TrainableExtractor(Extractor):
    """Abstract class for a trainable extractor
    
    A trainable extractor can be trained on a set of documents. This is usually backed by a machine learning model.
    """

    @property
    @abstractmethod
    def is_trained(self) -> bool:
        """Extractor training status."""

    @classmethod
    def parse_args(cls, parser: argparse.ArgumentParser):
        """Add arguments to parser when training."""

    @abstractmethod
    def train(
        self,
        documents: List[Tuple[Paper, AnnotationLayerInfo]],
        settings: List[str] = [],
        verbose=False,
    ):
        """Perform training

        ## Args:
            
        **documents** (`List[Tuple[lib.paper.Paper, Dict[str, lib.annotations.AnnotationLayer], lib.paper.AnnotationLayerInfo]]`): List of documents along with layer metadata.
        
        **verbose** (bool, optional): Display additional training informations. Defaults to False.
        """


from .segmentation import SegmentationCNNExtractor, SegmentationCRFExtractor, SegmentationStringCRFExtractor
from .header import HeaderCRFExtractor
from .results import ResultsCRFExtractor, ResultsStringCRFExtractor, ResultsLatexExtractor


ALL_EXTRACTORS = {}

for e in [SegmentationCNNExtractor, SegmentationCRFExtractor, SegmentationStringCRFExtractor, HeaderCRFExtractor, ResultsCRFExtractor, ResultsStringCRFExtractor, ResultsLatexExtractor]:
    ALL_EXTRACTORS[f"{e.class_.name}.{e.name}"] = e
