from typing import List, Dict, Tuple

from ..layers import Layer
from ..annotations import AnnotationLayer
from ..paper import AnnotationLayerInfo, Paper

class InvalidSchemaError(Exception):
    pass

class Extractor:
    name: str
    kind: str
    requirements: List[str]

    def apply(self, document: Paper, requirements: Dict[str, AnnotationLayer]) -> AnnotationLayer:
        raise NotImplementedError



class TrainableExtractor(Extractor):

    def train(self, documents: List[Tuple[Paper, Dict[str, AnnotationLayer], AnnotationLayerInfo]], verbose=False):
        raise NotImplementedError

