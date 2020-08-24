from typing import Dict
import re

from ...classes import ResultsAnnotationClass
from ...annotations import AnnotationLayer
from ...paper import Paper
from .. import Extractor


EXTRACTION_RE = re.compile(r"uri:extthm\.([\w\s]*)\.([0-9]+)", re.IGNORECASE)


def extract_results(box_name: str, box_group: int):
    global EXTRACTION_RE

    link_theorem_match = EXTRACTION_RE.search(box_name)
    if link_theorem_match is None:
        return None

    kind = link_theorem_match.group(1).lower()

    if kind not in ResultsAnnotationClass.labels:
        return None

    group = int(link_theorem_match.group(2))
    return kind, group


class ResultsExtractor(Extractor):
    name     = "latex"
    class_ = ResultsAnnotationClass()

    def __init__(self) -> None:
        pass

    def apply(self, document: Paper) -> AnnotationLayer:

        pdf_annots = document.get_pdf_annotations()
        pdf_annots.filter_map(extract_results)

        return pdf_annots
