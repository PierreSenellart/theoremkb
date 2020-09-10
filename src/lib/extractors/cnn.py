from typing import *
import os
import numpy as np
import numpy as np
import tensorflow as tf
import imageio
import argparse
import itertools
import tensorflow_datasets as tfds
import pickle

from . import TrainableExtractor
from ..classes import AnnotationClass
from ..annotations import AnnotationLayer
from ..paper import AnnotationLayerInfo, Paper
from ..misc.bounding_box import BBX, LabelledBBX
from ..misc import get_pattern
from ..misc.namespaces import *
from ..models import CNNTagger

BATCH_SIZE = 1
MAX_VOCAB = 10000
DEBUG_CNN = False

ENABLE_WORDS = True

if DEBUG_CNN:
    if not os.path.exists("/tmp/tkb"):
        os.mkdir("/tmp/tkb")


class CNNExtractor(TrainableExtractor):
    """Extracts annotations using a CNN."""

    model: CNNTagger

    @property
    def is_trained(self) -> bool:
        return self.model.is_trained()

    def __init__(self, prefix: str, name: str, class_: AnnotationClass) -> None:
        """Create the feature extractor."""

        os.makedirs(f"{prefix}/models", exist_ok=True)

        if len(name) == 0:
            self.name = "cnn"
        else:
            self.name = name + ".cnn"
        self.class_ = class_
        self.prefix = prefix
        self.model = CNNTagger(
            f"{prefix}/models/{self.class_.name}.{self.name}.cnn", self.class_.labels, ENABLE_WORDS
        )
        """CNN instance."""

    @property
    def description(self):
        return ""  # todo

    def _to_features(
        self, paper: Paper, vocabulary: Optional[dict]
    ) -> Tuple[np.ndarray, List[float]]:
        images = paper.render(
            max_height=512,
            max_width=512,
        )  # we assume that image fits in 512*512 ~ 200K pixels
        image_channels = images[0][0].shape[2]
        input_vector = np.zeros((len(images), 512, 512, image_channels))

        for i, (image, _) in enumerate(images):
            shape = image.shape
            input_vector[i, : shape[0], : shape[1], :] = image / 255.0

        if ENABLE_WORDS:
            input_text = np.zeros((len(images), 512, 512), dtype=int)
            for i, token in enumerate(paper.get_xml().getroot().findall(f".//{ALTO}String")):
                bbx = BBX.from_element(token)
                text = get_pattern(token.get("CONTENT"))
                scale = images[bbx.page_num - 1][1]

                input_text[
                    bbx.page_num - 1,
                    int(bbx.min_v * scale) : int(bbx.max_v * scale),
                    int(bbx.min_h * scale) : int(bbx.max_h * scale),
                ] = vocabulary.get(text, 1)

            return (input_vector, input_text), [x[1] for x in images]
        else:
            return input_vector, [x[1] for x in images]

    def _annots_to_labels(self, paper: Paper, layer: AnnotationLayerInfo) -> np.ndarray:
        scales = paper.get_render_scales(
            max_height=512,
            max_width=512,
        )

        ans = np.zeros((paper.n_pages, 512, 512, len(self.class_.labels) + 1))
        ans[:, :, :, 0] = 1

        label_to_index = {v: k + 1 for k, v in enumerate(self.class_.labels)}

        annotations = paper.get_annotation_layer(layer.id)
        for bbx in annotations.bbxs.values():
            scale = scales[bbx.page_num - 1]
            ans[
                bbx.page_num - 1,
                int(bbx.min_v * scale) : int(bbx.max_v * scale),
                int(bbx.min_h * scale) : int(bbx.max_h * scale),
                0,
            ] = 0
            label = label_to_index.get(bbx.label, 0)
            ans[
                bbx.page_num - 1,
                int(bbx.min_v * scale) : int(bbx.max_v * scale),
                int(bbx.min_h * scale) : int(bbx.max_h * scale),
                label,
            ] = 1

        if DEBUG_CNN:
            for p in range(ans.shape[0]):
                for ft in range(ans.shape[-1]):
                    imageio.imwrite(f"/tmp/tkb/{paper.id}-fsl-{p}-{ft}.png", ans[p, :, :, ft])

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
                slice = labels[
                    int(box.min_v * scale) : int(box.max_v * scale),
                    int(box.min_h * scale) : int(box.max_h * scale),
                ]

                votes = np.sum(slice, axis=(0, 1))

                label_id = np.argmax(votes)
                if label_id != 0:
                    label = self.class_.labels[label_id - 1]
                else:
                    label = "O"
                res.add_box(LabelledBBX.from_bbx(box, label, 0))

        return res

    def apply(self, paper: Paper, parameters: List[str]) -> AnnotationLayer:
        with open(f"{self.prefix}/models/{self.class_.name}.{self.name}.vocab", "rb") as f:
            vocab = pickle.load(f)

        input, page_scale = self._to_features(paper, vocab)

        INFERENCE_BATCH_SIZE = BATCH_SIZE * 2

        def labels_generator():
            for i in range(0, len(input), INFERENCE_BATCH_SIZE):
                tagged_images = self.model(input[i : i + INFERENCE_BATCH_SIZE])

                if DEBUG_CNN:
                    first_layer = self.model.first_layer((input[i : i + INFERENCE_BATCH_SIZE]))

                for j in range(tagged_images.shape[0]):
                    if DEBUG_CNN:
                        for ft in range(first_layer.shape[-1]):
                            imageio.imwrite(
                                f"/tmp/tkb/{paper.id}-fsl-{i+j}-{ft}.png", first_layer[j, :, :, ft]
                            )
                    yield tagged_images[j], page_scale[i + j]

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
        # train encoder
        if ENABLE_WORDS:
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
        else:
            vocab = None

        # train CNN

        def gen(labels_only=False):
            nonlocal documents, vocab
            for paper, annot in documents:
                if not labels_only:
                    input, _ = self._to_features(paper, vocab)
                lbl = self._annots_to_labels(paper, annot)
                if labels_only:
                    yield lbl
                else:
                    yield input, lbl

        if DEBUG_CNN:
            next(gen())
            exit(0)

        n_classes = len(self.class_.labels) + 1
        n_features = 3

        class_weights = {k: 0 for k in range(n_classes)}
        tot = 0

        for lbl in gen(labels_only=True):
            for i in range(1, n_classes):
                v = np.sum(lbl[:, :, :, i])
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
                        tf.TensorShape((None, 512, 512, n_features)),
                        tf.TensorShape((None, 512, 512)),
                    ),
                    tf.TensorShape((None, 512, 512, n_classes)),
                ),
            )
            .prefetch(4)
            .shuffle(buffer_size=4)
            .flat_map(lambda x, y: tf.data.Dataset.from_tensor_slices((x, y)))
            .shuffle(buffer_size=30)
            .batch(BATCH_SIZE)
        )

        print(f"Training CNN ! {len(documents)}")
        self.model.train(
            dataset,
            class_weights,
            n_features,
            MAX_VOCAB,
            from_latest=args.from_latest,
            name=self.name,
        )
