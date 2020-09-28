from typing import List

from .. import Extractor
from ...misc.namespaces import ALTO
from ...misc.bounding_box import LabelledBBX, BBX
from ...annotations import AnnotationLayer
from ...paper import Paper
from ...classes import MiscAnnotationClass


class AgreementExtractor(Extractor):
    """
    Computes where two layers don't agree and generate for each disagreement a box with the two labels.
    """

    class_ = MiscAnnotationClass()
    class_parameters = ["any", "any"]

    name = "agreement"
    description = ""

    def __init__(self) -> None:
        """Create the extractor."""

    def apply(self, document: Paper, parameters: List[str], _) -> AnnotationLayer:

        b1 = document.get_annotation_layer(parameters[0])
        b2 = document.get_annotation_layer(parameters[1])

        tokens = list(document.get_xml().getroot().findall(f".//{ALTO}String"))

        result = AnnotationLayer()

        for token in tokens:  # check if layers agree on token class.
            bbx = BBX.from_element(token)
            lbl1 = b1.get_label(bbx)
            lbl2 = b2.get_label(bbx)

            if lbl1 != lbl2:
                result.add_box(
                    LabelledBBX.from_bbx(
                        BBX.from_element(token), lbl1 + " - " + lbl2, 0
                    )
                )
        return result
