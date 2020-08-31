from ...misc.namespaces import *
from ..crf import CRFExtractor
from ...classes import SegmentationAnnotationClass

class SegmentationExtractor(CRFExtractor):
    name   = "crf"
    class_ =  SegmentationAnnotationClass()

    def __init__(self, prefix):
        super().__init__(prefix)

    def get_leaf_node(self) -> str:
        """Get the set of leaf nodes."""
        return f"{ALTO}TextLine"

class SegmentationStringExtractor(CRFExtractor):
    name   = "str.crf"
    class_ =  SegmentationAnnotationClass()

    def __init__(self, prefix):
        super().__init__(prefix)

    def get_leaf_node(self) -> str:
        """Get the set of leaf nodes."""
        return f"{ALTO}String"
