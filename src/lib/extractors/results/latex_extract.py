from typing import Dict
import re

from lib.layers import ResultsLayer

from ...annotations import AnnotationLayer
from ...paper import Paper
from .. import Extractor


EXTRACTION_RE = re.compile(r"uri:(theorem\.([\w\s]*)|proof)\.([0-9]+)",re.IGNORECASE)

def extract_results(box_name: str, box_group: int):
    global EXTRACTION_RE
    
    link_theorem_match = EXTRACTION_RE.search(box_name)
    if link_theorem_match is None:
        return None
    
    if link_theorem_match.group(1) == "proof":
        kind = "proof"
    else:
        kind = link_theorem_match.group(2).lower()
    
    if kind not in ResultsLayer.labels:
        return None

    group   = int(link_theorem_match.group(3))
    return kind, group


class ResultsExtractor(Extractor):
    name = "latex"
    kind = "results"
    requirements = []

    def __init__(self) -> None:
        pass

    def apply(self, document: Paper, requirements: Dict[str, AnnotationLayer]) -> AnnotationLayer:

        pdf_annots = document.get_pdf_annotations()
        pdf_annots.filter_map(extract_results)

        return pdf_annots
