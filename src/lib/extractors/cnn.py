from typing import List, Tuple, Iterator
import os
import numpy as np
import numpy as np
import tensorflow as tf
import imageio
import argparse

from . import TrainableExtractor
from ..classes import AnnotationClass
from ..annotations import AnnotationLayer
from ..paper import AnnotationLayerInfo, Paper
from ..misc.bounding_box import BBX, LabelledBBX
from ..misc import get_pattern
from ..misc.namespaces import *
from ..models import CNNTagger

BATCH_SIZE = 1
DEBUG_CNN = False

if DEBUG_CNN:
    if not os.path.exists("/tmp/tkb"):
        os.mkdir("/tmp/tkb")


class CNNExtractor(TrainableExtractor):
    """Extracts annotations using a CNN."""

    model: CNNTagger

    @property
    def is_trained(self) -> bool:
        return self.model.is_trained()

    def __init__(self, prefix: str) -> None:
        """Create the feature extractor."""

        os.makedirs(f"{prefix}/models", exist_ok=True)

        self.model = CNNTagger(f"{prefix}/models/{self.class_.name}.{self.name}.cnn", self.class_.labels)
        """CRF instance."""

    N_WORD_FEATURES = 16

    def _to_features(self, paper: Paper) -> np.ndarray:
        images = paper.render(
            height=768
        )  # we assume that image is in portrait, fit in 768*768 ~ 600K pixels
        image_channels = images[0][0].shape[2]

        n_features = (
            image_channels + self.N_WORD_FEATURES
        )  # + sum(len(features.columns) for features in raw_features.values())
        input_vector = np.zeros((len(images), 768, 768, n_features))

        for i, (image, _) in enumerate(images):
            shape = image.shape
            input_vector[i, : shape[0], : shape[1], :image_channels] = image / 255.0

        for token in paper.get_xml().getroot().findall(f".//{ALTO}String"):
            bbx = BBX.from_element(token)
            text = token.get("CONTENT")

            hash_bin = (
                np.binary_repr(hash(get_pattern(text)))
                .strip("-")
                .zfill(self.N_WORD_FEATURES)[: self.N_WORD_FEATURES]
            )
            hash_feature = 2 * np.array(list(hash_bin)).astype("float32") - 1

            scale = images[bbx.page_num - 1][1]

            input_vector[
                bbx.page_num - 1,
                int(bbx.min_v*scale) : int(bbx.max_v*scale),
                int(bbx.min_h*scale) : int(bbx.max_h*scale),
                image_channels:,
            ] = hash_feature

        if DEBUG_CNN:
            for i in range(n_features):
                imageio.imwrite(f"/tmp/tkb/{paper.id}-ft-{i}.png", input_vector[0, :, :, i])

        return input_vector, [x[1] for x in images]

    def _annots_to_labels(self, paper: Paper, layer: AnnotationLayerInfo) -> np.ndarray:
        ans = np.zeros((paper.n_pages, 768, 768, len(self.class_.labels) + 1))
        ans[:, :, :, 0] = 1

        label_to_index = {v: k + 1 for k, v in enumerate(self.class_.labels)}

        annotations = paper.get_annotation_layer(layer.id)
        for bbx in annotations.bbxs.values():
            ans[
                bbx.page_num - 1,
                int(bbx.min_v) : int(bbx.max_v),
                int(bbx.min_h) : int(bbx.max_h),
                0,
            ] = 0
            label = label_to_index.get(bbx.label, 0)
            ans[
                bbx.page_num - 1,
                int(bbx.min_v) : int(bbx.max_v),
                int(bbx.min_h) : int(bbx.max_h),
                label,
            ] = 1

        return ans

    def _labels_to_annots(
        self, paper: Paper, labels_by_page: Iterator[Tuple[np.ndarray, float]]
    ) -> AnnotationLayer:
        res = AnnotationLayer()

        root = paper.get_xml().getroot()
        pages = list(root.findall(f".//{ALTO}Page"))

        for p, (page, (labels, scale)) in enumerate(zip(pages, labels_by_page)):

            if DEBUG_CNN:
                if not os.path.exists("/tmp/tkb"):
                    os.mkdir("/tmp/tkb")
                # dump network output.
                for i, ft in enumerate(self.class_.labels):
                    imageio.imwrite(f"/tmp/tkb/{paper.id}-{p}-{ft}.png", labels[:, :, i + 1])
                imageio.imwrite(f"/tmp/tkb/{paper.id}-{p}-O.png", labels[:, :, 0])

            for token in page.findall(f".//{ALTO}String"):
                box = BBX.from_element(token)
                slice = labels[int(box.min_v*scale) : int(box.max_v*scale), int(box.min_h*scale) : int(box.max_h*scale)]

                votes = np.sum(slice, axis=(0, 1))

                label_id = np.argmax(votes)
                if label_id != 0:
                    label = self.class_.labels[label_id - 1]
                else:
                    label = "O"
                res.add_box(LabelledBBX.from_bbx(box, label, 0))

        return res

    def apply(self, paper: Paper, parameters: List[str]) -> AnnotationLayer:
        input_vector, page_scale = self._to_features(paper)

        INFERENCE_BATCH_SIZE = BATCH_SIZE * 8

        def labels_generator():
            for i in range(0, len(input_vector), INFERENCE_BATCH_SIZE):
                tagged_images = self.model(input_vector[i : i + INFERENCE_BATCH_SIZE])

                if DEBUG_CNN:
                    first_layer = self.model.first_layer(input_vector[i : i + INFERENCE_BATCH_SIZE])

                for j in range(tagged_images.shape[0]):
                    if DEBUG_CNN:
                        for ft in range(first_layer.shape[-1]):
                            imageio.imwrite(f"/tmp/tkb/{paper.id}-fsl-{i+j}-{ft}.png", first_layer[j,:,:,ft])
                    yield tagged_images[j], page_scale[i+j]

        return self._labels_to_annots(paper, labels_generator())

    def info(self):
        pass

    @classmethod
    def parse_args(cls, parser: argparse.ArgumentParser):
        parser.add_argument("--from_latest", action="store_true")

    def train(
        self,
        documents: List[Tuple[Paper, AnnotationLayerInfo]],
        args,
        verbose=False,
    ):
        # train tokenizer

        # train CNN
        def gen():
            nonlocal documents
            for paper, annot in documents:
                ft, _ = self._to_features(paper)
                lbl = self._annots_to_labels(paper, annot)
                for i in range(ft.shape[0]):
                    yield ft[i], lbl[i]

        next(gen())

        n_classes = len(self.class_.labels) + 1
        n_features = 3 + self.N_WORD_FEATURES
        # class_weights = {k: 0 for k in range(n_classes)}
        # tot = 0
        # for _,lbl in gen():
        #    for i in range(n_classes):
        #        v = np.sum(lbl[:,:,i])
        #        class_weights[i] += v
        #        tot += v
        # class_weights = {k: v/tot for k,v in class_weights.items()}
        class_weights = {
            0: 0.5498216987038238,
            1: 0.0007099176293894675,
            2: 0.0,
            3: 0.01285532526904739,
            4: 0.0019027098170397146,
            5: 0.003662149242459911,
            6: 0.3737182933705505,
            7: 0.030561784907767467,
            8: 0.0009232245488616031,
            9: 0.02584489651106011,
        }

        class_weights = {k: 1 / v if v != 0 else 0 for k, v in class_weights.items()}
        tot = sum(class_weights.values())
        class_weights = {k: v / tot for k, v in class_weights.items()}

        dataset = tf.data.Dataset.from_generator(
            gen,
            (tf.float32, tf.float32),
            (tf.TensorShape((768, 768, n_features)), tf.TensorShape((768, 768, n_classes))),
        )
        dataset = dataset.shuffle(buffer_size=20)
        dataset = dataset.batch(BATCH_SIZE)

        self.model.train(dataset, class_weights, n_features, from_latest=args.from_latest is not None)
