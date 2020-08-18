from lxml import etree as ET
from typing import List

from ...paper import Paper
from ...misc.namespaces import *
from ...features import FeatureExtractor
from ...features.String import StringFeaturesExtractor
from ...features.TextLine import TextLineFeaturesExtractor
from ...features.TextBlock import TextBlockFeaturesExtractor
from ...features.Page import PageFeaturesExtractor
from ..crf import CRFExtractor


def aggregate_features(values: List[dict], prefix: str):
    res = {}
    n = len(values)
    for lst in values:
        for key, value in lst.items():
            key = prefix+key
            if type(value) in [int, float, bool]:
                value = float(value)
                if key+".avg" not in res:
                    res[key+".avg"] = 0
                    res[key+".min"] = value
                    res[key+".max"] = value

                res[key+".avg"] += value / n
                res[key+".min"] = min(res[key+".min"], value)
                res[key+".max"] = max(res[key+".max"], value)

    return res


LINE_BASED = False


class HeaderFeaturesExtractor(FeatureExtractor):

    string_extractor: StringFeaturesExtractor
    textline_extractor: TextLineFeaturesExtractor
    textblock_extractor: TextBlockFeaturesExtractor
    page_extractor: PageFeaturesExtractor

    def __init__(self, root: ET.Element):
        self.string_extractor = StringFeaturesExtractor(root)
        self.textline_extractor = TextLineFeaturesExtractor(root)
        self.textblock_extractor = TextBlockFeaturesExtractor(root)
        self.page_extractor = PageFeaturesExtractor(root)

    def has(self, tag: str) -> bool:
        if LINE_BASED:
            return tag in [f"{ALTO}TextLine", f"{ALTO}TextBlock", f"{ALTO}Page"]
        else:
            return tag in [f"{ALTO}String", f"{ALTO}TextLine", f"{ALTO}TextBlock", f"{ALTO}Page"]

    def get(self, element: ET.Element) -> dict:
        if element.tag == f"{ALTO}Page":
            return self.page_extractor.get(element)
        elif element.tag == f"{ALTO}TextBlock":
            return self.textblock_extractor.get(element)
        elif element.tag == f"{ALTO}TextLine":
            ft = self.textline_extractor.get(element)
            ft = {
                **ft,
                **aggregate_features(
                    [
                        self.string_extractor.get(x)
                        for x in element
                        if x.tag == f"{ALTO}String"
                    ],
                    "String."
                ),
            }
            return ft
        elif element.tag == f"{ALTO}String":
            return self.string_extractor.get(element)
        else:
            raise KeyError

    def stop_at(self, tag: str) -> bool:
        if LINE_BASED:
            return tag == f"{ALTO}TextLine"
        else:
            return tag == f"{ALTO}String"


class HeaderExtractor(CRFExtractor):
    def __init__(self, prefix):
        super().__init__("crf", "header", [], prefix)

    def get_feature_extractor(self, paper: Paper, reqs) -> FeatureExtractor:
        return HeaderFeaturesExtractor(paper.get_xml().getroot())
