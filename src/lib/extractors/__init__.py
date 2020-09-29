import argparse
from abc import abstractmethod
from typing import List, Tuple, Optional


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

    """Extractor name"""
    name: str

    """Which class of annotations it extracts"""
    class_: AnnotationClass

    """Extractor description. Can be used to display used settings."""
    description: str = ""

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

        **document** (`lib.paper.Paper`): the article to annotate.
        ## Returns: `lib.annotations.AnnotationLayer`
        """

    def apply_and_save(
        self,
        document: Paper,
        parameters: List[str],
        args: Optional[argparse.Namespace] = None,
    ) -> AnnotationLayer:

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
