from typing import List
from lxml import etree as ET

from ..paper import AnnotationLayer
from ..misc.bounding_box import BBX

class Annotation:
    bbxs: List[BBX]
    label: str
    index: str

class InvalidSchemaError(Exception):
    pass

class Layer:
    name: str
    schema: dict
    labels: List[str]

    def __init__(self, name, schema):
        self.name   = name
        self.schema = schema

        try:
            if not schema["type"] == "object":
                raise InvalidSchemaError
            
            self.labels = schema["properties"]["label"]["enum"]
        except KeyError:
            raise InvalidSchemaError


    def pre_annotate(self, document) -> AnnotationLayer:
        raise Exception("Pre-annotate: not implemented.")


    def apply(self, document) -> AnnotationLayer:
        raise Exception("Pre-annotate: not implemented.")

    def train(self, documents):
        raise Exception("Pre-annotate: not implemented.")



# Re-exports
from .segmentation import SegmentationLayer
from .fulltext import FullTextLayer
from .results import ResultsLayer
