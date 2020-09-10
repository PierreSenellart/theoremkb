from typing import List, Tuple, Iterator
import os
import numpy as np
import numpy as np
import tensorflow as tf
import imageio
import argparse
import itertools
import pandas as pd

from . import TrainableExtractor
from ..classes import AnnotationClass
from ..annotations import AnnotationLayer
from ..paper import AnnotationLayerInfo, Paper
from ..misc.bounding_box import BBX, LabelledBBX
from ..misc import get_pattern
from ..misc.namespaces import *
from ..models import CNN1DTagger
import pickle


MAX_VOCAB = 10000
BATCH_SIZE = 32


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
        self.prefix = prefix
        self.model = CNN1DTagger(
            f"{prefix}/models/{self.class_.name}.{self.name}.model", self.class_.labels
        )
        """CNN instance."""

    def apply(self, paper: Paper, parameters: List[str]) -> AnnotationLayer:
        with open(f"{self.prefix}/models/{self.class_.name}.{self.name}.vocab", "rb") as f:
            vocab = pickle.load(f)

        input = self._to_features(paper, vocab)

        def gen():
            yield input

        input_gen = tf.data.Dataset.from_generator(
            gen,
            (tf.float32, tf.int32),
            (
                tf.TensorShape((None, input[0].shape[1])),
                tf.TensorShape((None, 1)),
            ),
        )

        res     = AnnotationLayer()
        root    = paper.get_xml().getroot()
        tokens  = root.findall(f".//{ALTO}String")

        i = 0
        for labels in self.model(input_gen):
            for j in range(labels.shape[0]):
                box = BBX.from_element(tokens[i+j])
                label_id = np.argmax(labels[j])

                if label_id != 0:
                    label = self.class_.labels[label_id - 1]
                else:
                    label = "O"
                    
                res.add_box(LabelledBBX.from_bbx(box, label, 0))
            i += j
        return res

    @property
    def description(self):
        return ""  # todo

    N_WORD_FEATURES = 21

    def _to_features(self, paper: Paper, vocabulary: dict) -> np.ndarray:
        features = paper.get_features(f"{ALTO}String")
        numeric_features = features.select_dtypes(include=["number", "bool"])
        categorical_features = features.select_dtypes(include=["category"])

        categorical_features = pd.get_dummies(categorical_features)

        text_idx = [
            [vocabulary.get(get_pattern(token.get("CONTENT")), 1)]
            for token in paper.get_xml().getroot().findall(f".//{ALTO}String")
        ]

        fts = pd.concat([numeric_features, categorical_features], axis=1)
        return fts.to_numpy(), np.array(text_idx)

    @classmethod
    def parse_args(cls, parser: argparse.ArgumentParser):
        parser.add_argument("--from_latest", action="store_true")

    def train(
        self,
        documents: List[Tuple[Paper, AnnotationLayerInfo]],
        args,
        verbose=False,
    ):
        n_classes = len(self.class_.labels) + 1

        print("building vocabulary")
        vocab = {}
        for paper, _ in documents:
            for token in paper.get_xml().getroot().findall(f".//{ALTO}String"):
                bbx = BBX.from_element(token)
                text = get_pattern(token.get("CONTENT"))
                vocab[text] = vocab.get(text, 0) + 1

        sorted_vocab = sorted(vocab.items(), key=lambda x: x[1], reverse=True)
        print(sorted_vocab[:10])
        print(sorted_vocab[-10:])
        sorted_vocab = list(map(lambda x: x[0], sorted_vocab))[: MAX_VOCAB - 2]
        vocab = {x: y + 2 for y, x in enumerate(sorted_vocab)}

        with open(f"{self.prefix}/models/{self.class_.name}.{self.name}.vocab", "wb") as f:
            pickle.dump(vocab, f)

        n_classes = len(self.class_.labels) + 1

        def gen(labels_only=False):
            nonlocal documents, vocab, n_classes
            for paper, annot in documents:
                if not labels_only:
                    ft = self._to_features(paper, vocab)

                annotations = paper.get_annotation_layer(annot.id)
                lbl = [
                    annotations.get_label(BBX.from_element(node))
                    for node in paper.get_xml().getroot().findall(f".//{ALTO}String")
                ]

                label_to_index = {v: k + 1 for k, v in enumerate(self.class_.labels)}
                np_lbl = np.zeros((len(lbl), n_classes))

                for i, l in enumerate(lbl):
                    np_lbl[i, label_to_index.get(l, 0)] = 1

                if labels_only:
                    yield np_lbl
                else:
                    yield ft, np_lbl

        (a, b), test_lbl = next(gen())

        class_weights = {k: 0 for k in range(n_classes)}
        tot = 0

        for lbl in gen(labels_only=True):
            for i in range(1, n_classes):
                v = np.sum(lbl[:, i])
                class_weights[i] += v
                tot += v

        class_weights = {k: tot / v if v != 0 else 0 for k, v in class_weights.items()}
        tot = sum(class_weights.values())
        print("tot:", tot)
        class_weights = {k: v / tot for k, v in class_weights.items()}

        print("Computed class weights:")
        for k, cl in enumerate(self.class_.labels):
            print(k, "{:10}: {:6f}".format(cl, class_weights[k + 1]))

        dataset = (
            tf.data.Dataset.from_generator(
                gen,
                ((tf.float32, tf.int32), tf.float32),
                (
                    (
                        tf.TensorShape((None, a.shape[1])),
                        tf.TensorShape((None, 1)),
                    ),
                    tf.TensorShape((None, n_classes)),
                ),
            )
            .cache()
            .prefetch(4)
        )

        self.model.train(
            dataset,
            class_weights,
            a.shape[1],
            MAX_VOCAB,
            from_latest=args.from_latest,
            name=self.name,
        )
