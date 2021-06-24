"""A naive algorithm for results extraction"""

from ...classes import ResultsAnnotationClass
from ...annotations import AnnotationLayer
from ...paper import Paper
from ...misc.bounding_box import LabelledBBX
from .. import Extractor
from ...misc.namespaces import *
from ...misc.bounding_box import BBX


class NaiveExtractor(Extractor):
    name = "naive"
    class_ = ResultsAnnotationClass()
    description = ""

    def __init__(self) -> None:
        pass

    def apply(self, document: Paper, _parameters, _args) -> AnnotationLayer:
        res = AnnotationLayer()

        features = document.get_features(
            f"{ALTO}String", standardize=True, add_context=False
        )
        tokens = document.get_xml().getroot().findall(f".//{ALTO}String")

        in_result = None
        group = 0

        for i, token in enumerate(tokens):

            ft = features.iloc[i]

            if (
                ft["String.word_position"] == "start"
                and ft["String.word_pattern"] in self.class_.labels
                and (ft["String.italic"] or ft["String.bold"])
            ):
                in_result = ft["String.word_pattern"]
                group += 1
            elif (
                ft["String.word_position"] == "start"
                and ft["TextLine.line_position"] == "start"
            ):
                in_result = None

            if in_result is not None:
                res.add_box(
                    LabelledBBX.from_bbx(BBX.from_element(token), in_result, group)
                )
            else:
                res.add_box(LabelledBBX.from_bbx(BBX.from_element(token), "O", 0))

        return res
