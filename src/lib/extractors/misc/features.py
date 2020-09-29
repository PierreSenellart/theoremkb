import numpy as np
from typing import List

from .. import Extractor
from ...misc.namespaces import ALTO
from ...misc.bounding_box import LabelledBBX, BBX
from ...misc import filter_nan
from ...annotations import AnnotationLayer
from ...paper import Paper
from ...classes import MiscAnnotationClass


def check_dtype(obj):
    """
    Convert special types to native types so that they
    can be transformed to json.
    """
    if type(obj) == dict:
        return {k: check_dtype(v) for k, v in obj.items()}
    elif type(obj) == np.int64:
        return int(obj)
    elif type(obj) == np.bool_:
        return bool(obj)
    else:
        return obj


class FeatureExtractor(Extractor):
    """
    For each token generates metadata containing the computed features.
    """

    class_ = MiscAnnotationClass()
    class_parameters = []

    @property
    def name(self):
        return "features." + self.leaf_node

    def __init__(self, leaf_node) -> None:
        """Create the feature extractor."""
        self.leaf_node = leaf_node

    def apply(self, document: Paper, parameters: List[str], _) -> AnnotationLayer:
        leaf_node = f"{ALTO}{self.leaf_node}"
        tokens = list(document.get_xml().getroot().findall(f".//{leaf_node}"))
        features = document.get_features(leaf_node, standardize=False).to_dict(
            "records"
        )

        result = AnnotationLayer()

        for counter, (token, ft) in enumerate(zip(tokens, features)):
            ft_hiearch = {}  # build hierarchical feature set.
            for k, v in ft.items():
                a, b = k.split(".", 1)  # we un-flatten the features.
                if a not in ft_hiearch:
                    ft_hiearch[a] = {}
                ft_hiearch[a][b] = v

            result.add_box(
                LabelledBBX.from_bbx(
                    BBX.from_element(token),
                    "",
                    counter,
                    user_data=check_dtype(filter_nan(ft_hiearch)),
                )
            )
        return result
