from ...misc.namespaces import *
from ..crf import CRFExtractor

LINE_BASED = True

class SegmentationExtractor(CRFExtractor):
    def __init__(self, prefix):
        super().__init__("crf", "segmentation", prefix)

    def get_leaf_node(self) -> str:
        """Get the set of leaf nodes."""

        if LINE_BASED:
            return f"{ALTO}TextLine"
        else:
            return f"{ALTO}String"
