from typing import Dict

from ...annotations import AnnotationLayer
from ...paper import Paper
from .. import Extractor


class ResultsExtractor(Extractor):
    name = "latex"
    kind = "results"
    requirements = []

    def __init__(self) -> None:
        pass

    def apply(self, document: Paper, requirements: Dict[str, AnnotationLayer]) -> AnnotationLayer:
        pdf_annots = document.get_pdf_annotations()

        return pdf_annots
        