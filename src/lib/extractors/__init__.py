from abc import abstractmethod
from typing import List, Dict, Tuple

from ..annotations import AnnotationLayer
from ..paper import AnnotationLayerInfo, Paper


class Extractor:
    """Abstract class for an annotation layer builder"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Extractor name"""
    
    @name.setter
    def name(self, v):
        self._name = v
    
    @property
    @abstractmethod
    def kind(self) -> str:
        """Which kind of annotations it extracts"""
    
    @property
    @abstractmethod
    def requirements(self) -> List[str]:
        """Required annotations layers"""

    @abstractmethod
    def apply(self, document: Paper, requirements: Dict[str, AnnotationLayer]) -> AnnotationLayer:
        """Create an annotation layer from the given article.

        ## Args:

        **document** (`lib.paper.Paper`): the article to annotate.

        **requirements** (`Dict[str, lib.annotations.AnnotationLayer`]): additional layers required for extraction.

        ## Returns: `lib.annotations.AnnotationLayer`
        """



class TrainableExtractor(Extractor):
    """Abstract class for a trainable extractor
    
    A trainable extractor can be trained on a set of documents. This is usually backed by a machine learning model.
    """

    @property
    @abstractmethod
    def is_trained(self) -> bool:
        """Extractor training status."""

    @abstractmethod
    def train(self, documents: List[Tuple[Paper, Dict[str, AnnotationLayer], AnnotationLayerInfo]], verbose=False):
        """Perform training

        ## Args:
            
        **documents** (`List[Tuple[lib.paper.Paper, Dict[str, lib.annotations.AnnotationLayer], lib.paper.AnnotationLayerInfo]]`): List of documents along with required annotation layers and layer metadata.
        
        **verbose** (bool, optional): Display additional training informations. Defaults to False.
        """

