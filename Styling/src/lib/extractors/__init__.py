"""
## Extractors

An extractor takes a paper as an input, optionally with several annotations layers of class specified by the requirements property. 
It outputs an annotation layer that can be displayed and/or saved.
The extractor might be trainable, for example when machine learning models are used.
"""


import argparse
from abc import abstractmethod
from typing import List, Tuple, Optional


from ..annotations import AnnotationLayer
from ..classes import AnnotationClass
from ..paper import AnnotationLayerInfo, Paper
from ..misc.namespaces import *



class Extractor:
    """Abstract class for an extractor
    
    An extractor is an algorithm applied to a document, it produces an `lib.annotations.AnnotationLayer` that can then be used for training purposes or displayed by the UI.
    """

    name: str
    """Extractor name"""

    class_: AnnotationClass
    """Which class of annotations it extracts"""

    description: str = ""
    """Extractor description. Can be used to display used settings."""

    @property
    def class_parameters(self) -> List[str]:
        """Layer class the extractor needs to perform its work. Can be 'any' for a general purpose extractor"""
        return []

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        """Add arguments to the parser when applying the extractor."""

    @abstractmethod
    def apply(
        self, document: Paper, parameters: List[str], args: argparse.Namespace
    ) -> AnnotationLayer:
        """Create an annotation layer from the given article.

        ## Args:

        * **document** (`lib.paper.Paper`): the article to annotate.
        * **parameters** (`List[str]`): layer IDs if some have been requested by `Extractor.class_parameters`.

        ## Returns: `lib.annotations.AnnotationLayer`
        """

    def apply_and_save(
        self,
        document: Paper,
        parameters: List[str],
        args: Optional[argparse.Namespace] = None,
    ) -> AnnotationLayer:
        """
        General-purpose procedure to apply an extractor to a paper.
        """

        if args is None:
            parser = argparse.ArgumentParser()
            self.add_args(parser)
            args = parser.parse_args([])

        annotations = self.apply(document, parameters, args)
        annotations = annotations.reduce()
        annotations.filter(lambda x: x.label != "O")

        return document.add_annotation_layer(self.class_.name, content=annotations)


class TrainableExtractor(Extractor):
    """Abstract class for a trainable extractor

    A trainable extractor can be trained on a set of documents. This is usually backed by a machine learning model.
    """

    @property
    @abstractmethod
    def is_trained(self) -> bool:
        """Extractor training status."""

    @staticmethod
    def add_train_args(parser: argparse.ArgumentParser):
        """Add arguments to the parser when training the extractor."""

    @abstractmethod
    def train(
        self,
        documents: List[Tuple[Paper, AnnotationLayerInfo]],
        args: argparse.Namespace,
    ):
        """Perform training

        ## Args:

        **documents** (`List[Tuple[lib.paper.Paper, Dict[str, lib.annotations.AnnotationLayer], lib.paper.AnnotationLayerInfo]]`): List of documents along with layer metadata.

        **args** Command line arguments.
        """
