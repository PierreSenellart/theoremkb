from typing import List

from .. import Extractor
from ...misc.namespaces import *
from ...misc.bounding_box import LabelledBBX, BBX
from ...annotations import AnnotationLayer
from ...paper import Paper
from ...classes import MiscAnnotationClass

class AgreementExtractor(Extractor):

    class_           = MiscAnnotationClass()
    class_parameters = ["any", "any"]

    name             = "agreement"
    description      = ""

    def __init__(self) -> None:
        """Create the extractor."""

    def apply(self, paper: Paper, parameters: List[str]) -> AnnotationLayer:

        b1 = None
        b2 = None
        for layer in paper.layers:
            if layer.group_id == parameters[0]:
                b1 = paper.get_annotation_layer(layer.id)
            elif layer.group_id == parameters[1]:
                b2 = paper.get_annotation_layer(layer.id)
        
        tokens      = list(paper.get_xml().getroot().findall(f".//{ALTO}String"))

        result = AnnotationLayer()

        for token in tokens:
            bbx = BBX.from_element(token)
            lbl1 = b1.get_label(bbx)
            lbl2 = b2.get_label(bbx)

            if lbl1 != lbl2:
                result.add_box(LabelledBBX.from_bbx(BBX.from_element(token), lbl1 + " - " + lbl2, 0))
        return result
        
