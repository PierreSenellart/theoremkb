from ...misc.namespaces import *
from ..crf import CRFExtractor

class HeaderExtractor(CRFExtractor):
    def __init__(self, prefix):
        super().__init__("crf", "header", prefix)


    def get_leaf_node(self) -> str:
        """Get the set of leaf nodes."""
        return f"{ALTO}String"
