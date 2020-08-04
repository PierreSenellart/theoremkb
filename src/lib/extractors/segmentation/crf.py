

from lxml import etree as ET
from collections import namedtuple
from typing import List, Dict, Tuple
from tqdm import tqdm
import os

from ...annotations import AnnotationLayer
from ...paper import AnnotationLayerInfo, Paper
from ...misc.bounding_box import BBX, LabelledBBX
from ...misc.namespaces import *
from ...features import FeatureExtractor
from ...features.String import StringFeaturesExtractor
from ...features.TextLine import TextLineFeaturesExtractor
from ...models import CRFTagger
from ..crf import CRFExtractor


def aggregate_features(values: List[dict]):
    res = {}
    n = len(values)
    for lst in values:
        for key, value in lst.items():
            if type(value) in [int, float, bool]:
                if key not in res:
                    res[key] = 0
                
                res[key] += float(value)/n
    return res
            



LINE_BASED = False

class SegmentationFeaturesExtractor(FeatureExtractor):

    string_extractor: StringFeaturesExtractor
    textline_extractor: TextLineFeaturesExtractor

    def __init__(self, root: ET.Element):
        self.string_extractor = StringFeaturesExtractor(root)
        self.textline_extractor = TextLineFeaturesExtractor(root)

    def has(self, tag: str) -> bool:
        if LINE_BASED:
            return tag == f"{ALTO}TextLine"
        else:
            return tag in [f"{ALTO}String", f"{ALTO}TextLine"]

    def get(self, element: ET.Element) -> dict:
        if element.tag == f"{ALTO}TextLine":
            ft = self.textline_extractor.get(element)
            ft = {**ft, **aggregate_features([self.string_extractor.get(x)
                                              for x in element if x.tag == f"{ALTO}String"])}
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


class SegmentationExtractor(CRFExtractor):
    def __init__(self, prefix):
        super().__init__("crf", "segmentation", [], prefix)

    def _get_feature_extractor(self, paper: Paper, reqs) -> FeatureExtractor:
        return SegmentationFeaturesExtractor(paper.get_xml().getroot())
