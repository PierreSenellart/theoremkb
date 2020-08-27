from ...misc.namespaces import *
from ..crf import CRFExtractor
from ...classes import SegmentationAnnotationClass

class SegmentationExtractor(CRFExtractor):
    def __init__(self, prefix):
        super().__init__("crf", SegmentationAnnotationClass(), prefix)

    def get_leaf_node(self) -> str:
        """Get the set of leaf nodes."""
        return f"{ALTO}TextLine"

class SegmentationStringExtractor(CRFExtractor):
    def __init__(self, prefix):
        super().__init__("str.crf", SegmentationAnnotationClass(), prefix)

    def get_leaf_node(self) -> str:
        """Get the set of leaf nodes."""
        return f"{ALTO}String"
