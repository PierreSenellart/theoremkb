"""Extractor for PDFs that have been compiled with the latex extraction script

This extractor is used to build a _gold-standard_ dataset for results extraction. 
It requires PDFs that have been extracted using the `tools/latex_extract/extract_theorems.py` script.
"""

import re

from ...classes import ResultsAnnotationClass
from ...annotations import AnnotationLayer
from ...paper import Paper
from .. import Extractor
from ...misc.namespaces import ALTO


EXTRACTION_RE = re.compile(r"uri:extthm\.([\w\s]*)\.([0-9]+)", re.IGNORECASE)

# we only keep pdf links that are generated by the latex script.
def extract_results(box_name: str, _box_group: int):
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
    name = "latex"
    class_ = ResultsAnnotationClass()
    description = ""

    def __init__(self) -> None:
        pass

    def apply(self, document: Paper, _parameters, _args) -> AnnotationLayer:

        box_validator = document.get_box_validator(self.class_)

        pdf_annots = document.get_pdf_annotations()  # get PDF annotations as a layer
        pdf_annots.filter_map(extract_results)  # filter and rename result boxes
        pdf_annots.filter(
            box_validator
        )  # keep boxes that are allowed (= in body or annex)
        # project boxes on textual tokens.

        return document.apply_annotations_on(pdf_annots, f"{ALTO}String")