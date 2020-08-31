from .latex_extract import ResultsExtractor as ResultsLatexExtractor
from ...classes import ResultsAnnotationClass
from ...misc.namespaces import *
from ..crf import CRFExtractor

class ResultsCRFExtractor(CRFExtractor):

    name    = "crf"
    class_  = ResultsAnnotationClass()


    def __init__(self, prefix):
        super().__init__(prefix)

    def get_leaf_node(self) -> str:
        """Get the set of leaf nodes."""
        return f"{ALTO}TextLine"
        
class ResultsStringCRFExtractor(CRFExtractor):

    name     = "str.crf"
    class_   = ResultsAnnotationClass()


    def __init__(self, prefix):
        super().__init__(prefix)

    def get_leaf_node(self) -> str:
        """Get the set of leaf nodes."""
        return f"{ALTO}String"
        