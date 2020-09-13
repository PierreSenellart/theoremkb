from typing import List, Tuple, Iterator, Optional
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
from ..misc import get_pattern, ensuredir, embeddings
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

    @property
    def _model_dir(self) -> str:
        return f"{self.prefix}/models/{self.class_.name}.{self.name}/"

    @property
    def _model_path(self) -> str:
        return f"{self._model_dir}/cnn"

    @property
    def _vocab_path(self) -> str:
        return f"{self._model_dir}/vocab"

    def __init__(self, prefix: str, name: str, class_: AnnotationClass) -> None:
        """Create the feature extractor."""

        self.class_ = class_
        self.prefix = prefix
        self.name = "cnn1d" if len(name) == 0 else f"{name}.cnn1d"
        self.model = CNN1DTagger(self._model_path, self.class_.labels)

        ensuredir(self._model_dir)
        ensuredir(self._model_path)

    @property
    def description(self):
        return self.model.description()


    def _to_features(self, paper: Paper, vocabulary: Optional[dict]):
        features = paper.get_features(f"{ALTO}String")
        numeric_features = features.select_dtypes(include=["number", "bool"])
        categorical_features = features.select_dtypes(include=["category"])
        categorical_features = pd.get_dummies(categorical_features)
        fts = pd.concat([numeric_features, categorical_features], axis=1)

        if vocabulary is not None:
            text_idx = [
                [vocabulary.get(get_pattern(token.get("CONTENT")), 1)]
                for token in paper.get_xml().getroot().findall(f".//{ALTO}String")
            ]
            return fts.to_numpy(), np.array(text_idx)
        else:
            return fts.to_numpy()

    def apply(self, paper: Paper, parameters: List[str], args) -> AnnotationLayer:
        
        if self.model.params.word_embeddings > 0:
            with open(self._vocab_path, "rb") as f:
                vocab = pickle.load(f)
        else:
            vocab = None

        input = self._to_features(paper, vocab)
        input_gen = tf.data.Dataset.from_tensors(input)

        res = AnnotationLayer()
        root = paper.get_xml().getroot()
        tokens = root.findall(f".//{ALTO}String")

        i = 0
        for labels in self.model(input_gen):
            for j in range(labels.shape[0]):
                box = BBX.from_element(tokens[i + j])
                label_id = np.argmax(labels[j])

                if label_id != 0:
                    label = self.class_.labels[label_id - 1]
                else:
                    label = "O"

                res.add_box(LabelledBBX.from_bbx(box, label, 0))
            i += j
        return res

    @staticmethod
    def add_train_args(parser: argparse.ArgumentParser):
        parser.add_argument("--from-latest", action="store_true")
        parser.add_argument("--reload-vocab", action="store_false")

        parser.add_argument("-w", "--word-embeddings", type=int, default=10000)
        parser.add_argument("-c", "--context-size", type=int, default=64)
        parser.add_argument("--balance-classes", action="store_true")
        parser.add_argument("--n-epoch", type=int, default=100)

    def _annots_to_labels(self, paper, annot):
        annotations = paper.get_annotation_layer(annot.id)
        lbl = [
            annotations.get_label(BBX.from_element(node))
            for node in paper.get_xml().getroot().findall(f".//{ALTO}String")
        ]

        label_to_index = {v: k + 1 for k, v in enumerate(self.class_.labels)}
        np_lbl = np.zeros((len(lbl), len(self.class_.labels) + 1))

        for i, l in enumerate(lbl):
            np_lbl[i, label_to_index.get(l, 0)] = 1
        return np_lbl

    def compute_class_weights(self, n_classes, labels_generator) -> dict:
        class_weights = {k: 0 for k in range(n_classes)}
        total = 0
        count_sentences = 0

        for lbl in labels_generator:
            count_sentences += lbl.shape[0]
            for i in range(1, n_classes):
                v = np.sum(lbl[:, i])
                class_weights[i] += v
                total += v

        class_weights = {k: total / v if v != 0 else 0 for k, v in class_weights.items()}
        total = sum(class_weights.values())
        return {k: v / total for k, v in class_weights.items()}
    
    def train(
        self,
        documents: List[Tuple[Paper, AnnotationLayerInfo]],
        args,
    ):
        n_classes = len(self.class_.labels) + 1

        if args.word_embeddings > 0:
            if args.reload_vocab or args.from_latest:
                try:
                    with open(self._vocab_path, "rb") as f:
                        vocab = pickle.load(f)
                except:
                    print("Unable to reload vocabulary file.")
                    exit(-1)
            else:
                print("building vocabulary")
                vocab = embeddings.build_vocabulary(args.word_embeddings, documents)

                with open(self._vocab_path, "wb") as f:
                    pickle.dump(vocab, f)
        else:
            vocab = None

        n_classes = len(self.class_.labels) + 1

        # sample generator
        def gen(labels_only=False):
            nonlocal documents, vocab, n_classes
            for paper, annot in documents:
                if not labels_only:
                    ft = self._to_features(paper, vocab)

                lbl = self._annots_to_labels(paper, annot)

                if labels_only:
                    yield lbl
                else:
                    yield ft, lbl

        # class imbalance.
        if args.balance_classes:
            class_weights = self.compute_class_weights(
                len(self.class_.labels) + 1, gen(labels_only=True)
            )
            print("Computed class weights:")
            for k, cl in enumerate(self.class_.labels):
                print(k, "{:10}: {:6f}".format(cl, class_weights[k + 1]))
        else:
            class_weights = None

        # generate a sampe to get the number of features.
        (a, b), test_lbl = next(gen())

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
            name=self.name,
            **vars(args)
        )
