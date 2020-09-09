from typing import List
import numpy as np


from .. import Extractor
from ...misc.namespaces import *
from ...misc.bounding_box import LabelledBBX, BBX
from ...annotations import AnnotationLayer
from ...paper import Paper
from ...classes import MiscAnnotationClass

def check_dtype(obj):
    if type(obj) == dict:
        return {k: check_dtype(v) for k,v in obj.items()}
    elif type(obj) == np.int64:
        return int(obj)
    elif type(obj) == np.bool_:
        return bool(obj)
    else:
        return obj

class FeatureExtractor(Extractor):

    class_           = MiscAnnotationClass()
    class_parameters = []

    @property
    def name(self):
        return "features."+self.leaf_node

    @property
    def description(self):
        description = ""

    def __init__(self, leaf_node) -> None:
        """Create the feature extractor."""
        self.leaf_node = leaf_node

    def apply(self, paper: Paper, parameters: List[str]) -> AnnotationLayer:

        leaf_node   = f"{ALTO}{self.leaf_node}"
        tokens      = list(paper.get_xml().getroot().findall(f".//{leaf_node}"))
        features    = paper.get_features(leaf_node, standardize=False).to_dict('records')

        result = AnnotationLayer()

        for counter, (token, ft) in enumerate(zip(tokens, features)):
            ft_hiearch = {}
            for k,v in ft.items():
                a,b = k.split(".", 1)
                if a not in ft_hiearch:
                    ft_hiearch[a] = {}
                ft_hiearch[a][b] = v

            result.add_box(LabelledBBX.from_bbx(BBX.from_element(token), "", counter, user_data=check_dtype(ft_hiearch)))
        return result
        
