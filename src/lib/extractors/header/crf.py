from ...misc.namespaces import *
from ..crf import CRFExtractor
from ...classes import HeaderAnnotationClass

class HeaderExtractor(CRFExtractor):

    name    = "crf"
    class_  = HeaderAnnotationClass()

    def __init__(self, prefix):
        super().__init__(prefix)

    def get_leaf_node(self) -> str:
        """Get the set of leaf nodes."""
        return f"{ALTO}String"
