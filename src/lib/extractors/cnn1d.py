from typing import List, Tuple, Iterator
import os
import numpy as np
import numpy as np
import tensorflow as tf
import imageio
import argparse
import itertools

from . import TrainableExtractor
from ..classes import AnnotationClass
from ..annotations import AnnotationLayer
from ..paper import AnnotationLayerInfo, Paper
from ..misc.bounding_box import BBX, LabelledBBX
from ..misc import get_pattern
from ..misc.namespaces import *
from ..models import CNN1DTagger


class CNN1DExtractor(TrainableExtractor):

    model: CNN1DTagger

    @property
    def is_trained(self) -> bool:
        return self.model.is_trained()

    def __init__(self, prefix: str, name: str, class_: AnnotationClass) -> None:
        """Create the feature extractor."""

        os.makedirs(f"{prefix}/models", exist_ok=True)

        if len(name) == 0:
            self.name = "cnn1d"
        else:
            self.name = name + ".cnn1d"
        self.class_ = class_

        self.model = CNN1DTagger(
            f"{prefix}/models/{self.class_.name}.{self.name}.model", self.class_.labels
        )
        """CNN instance."""

    @property
    def description(self):
        return ""  # todo

    N_WORD_FEATURES = 21

    def _to_features(self, paper: Paper) -> np.ndarray:
        features = paper.get_features(f"{ALTO}String")
        numeric_features = features.select_dtypes(include=["number", "bool"])
        categorical_features = features.select_dtypes(include=["category"])

        print("Numeric features:", len(numeric_features.columns))
        print("Categorical:", len(categorical_features.columns))

    def train(
        self,
        documents: List[Tuple[Paper, AnnotationLayerInfo]],
        args,
        verbose=False,
    ):
        n_classes = len(self.class_.labels) + 1

        def gen(labels_only=False):
            nonlocal documents
            for paper, annot in documents:
                if not labels_only:
                    ft, _ = self._to_features(paper)

                annotations = paper.get_annotation_layer(annot.id)
                lbl = [
                    annotations.get(BBX.from_element(node))
                    for node in paper.get_xml().getroot().findall(f".//{ALTO}String")
                ]
                if labels_only:
                    yield lbl
                else:
                    yield ft, lbl

        test_ft, test_lbl = next(gen())