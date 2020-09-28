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
from ..misc import get_pattern, ensuredir, embeddings
from ..misc.namespaces import *
from ..models.cnn import CNNTagger


class CNNExtractor(TrainableExtractor):
    """Extracts annotations using a CNN."""

    model: CNNTagger

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

        self.prefix = prefix
        self.name = "cnn" if len(name) == 0 else f"{name}.cnn"
        self.class_ = class_
        self.model = CNNTagger(self._model_path, self.class_.labels)

        ensuredir(self._model_dir)
        ensuredir(self._model_path)

    @property
    def description(self):
        return self.model.description()

    def _to_features(
        self,
        paper: Paper,
        vocabulary: Optional[dict],
        render_size: int,
    ):
        images = paper.render(max_height=render_size, max_width=render_size)
        image_channels = images[0][0].shape[2]
        input_vector = np.zeros((len(images), render_size, render_size, image_channels))

        for i, (image, _) in enumerate(images):
            shape = image.shape
            input_vector[i, : shape[0], : shape[1], :] = image / 255.0

        if vocabulary is not None:
            input_text = np.zeros((len(images), render_size, render_size), dtype=int)
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

    def _labels_to_annots(
        self,
        paper: Paper,
        labels_by_page: Iterator[Tuple[np.ndarray, float]],
        debug: bool = False,
    ) -> AnnotationLayer:
        res = AnnotationLayer()

        root = paper.get_xml().getroot()
        pages = list(root.findall(f".//{ALTO}Page"))

        for p, (page, (labels, scale)) in enumerate(zip(pages, labels_by_page)):

            if debug:
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

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        parser.add_argument("-b", "--batch-size", type=int, default=1)
        parser.add_argument("-d", "--debug", action="store_true")

    def apply(
        self, paper: Paper, parameters: List[str], args: argparse.Namespace
    ) -> AnnotationLayer:
        if self.model.params.word_embeddings > 0:
            with open(self._vocab_path, "rb") as f:
                vocab = pickle.load(f)
        else:
            vocab = None

        input, page_scale = self._to_features(paper, vocab, self.model.params.render_size)

        def labels_generator():  # apply the model and yield labeled pages.
            for i in range(0, len(input), args.batch_size):
                tagged_images = self.model(input[i : i + args.batch_size])

                if args.debug:
                    first_layer = self.model.first_layer((input[i : i + args.batch_size]))

                for j in range(tagged_images.shape[0]):
                    if args.debug:
                        for ft in range(first_layer.shape[-1]):
                            imageio.imwrite(
                                f"/tmp/tkb/{paper.id}-fsl-{i+j}-{ft}.png", first_layer[j, :, :, ft]
                            )
                    yield tagged_images[j], page_scale[i + j]

        return self._labels_to_annots(paper, labels_generator(), args.debug)

    def _annots_to_labels(
        self, paper: Paper, layer: AnnotationLayerInfo, render_size: int, debug: bool = False
    ) -> np.ndarray:
        scales = paper.get_render_scales(
            max_height=render_size,
            max_width=render_size,
        )

        ans = np.zeros((paper.n_pages, render_size, render_size, len(self.class_.labels) + 1))
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

        if debug:
            for p in range(ans.shape[0]):
                for ft in range(ans.shape[-1]):
                    imageio.imwrite(f"/tmp/tkb/{paper.id}-fsl-{p}-{ft}.png", ans[p, :, :, ft])

        return ans

    def compute_class_weights(self, n_classes, labels_generator) -> dict:
        class_weights = {k: 0 for k in range(n_classes)}
        total = 0

        for lbl in labels_generator:
            for i in range(1, n_classes):
                v = np.sum(lbl[:, :, :, i])
                class_weights[i] += v
                total += v

        class_weights = {k: total / v if v != 0 else 0 for k, v in class_weights.items()}
        total = sum(class_weights.values())
        return {k: v / total for k, v in class_weights.items()}

    def info(self):
        pass

    @staticmethod
    def add_train_args(parser: argparse.ArgumentParser):
        parser.add_argument("--from-latest", action="store_true")
        parser.add_argument("--reload-vocab", action="store_true")

        parser.add_argument("-w", "--word-embeddings", type=int, default=10000)
        parser.add_argument("-r", "--render-size", type=int, default=512)
        parser.add_argument("--balance-classes", action="store_true")

    def train(
        self,
        documents: List[Tuple[Paper, AnnotationLayerInfo]],
        args: argparse.Namespace,
    ):
        # train encoder
        if args.word_embeddings > 0:
            if not (args.reload_vocab or args.from_latest):
                print("building vocabulary")
                vocab = embeddings.build_vocabulary(args.word_embeddings, documents[:10])

                with open(self._vocab_path, "wb") as f:
                    pickle.dump(vocab, f)
            else:
                try:
                    with open(self._vocab_path, "rb") as f:
                        vocab = pickle.load(f)
                except:
                    print("Unable to reload vocabulary file.")
                    exit(-1)
        else:
            vocab = None

        # train CNN
        # > sample generator.
        def gen(labels_only=False):
            nonlocal documents, vocab
            for paper, annot in documents:
                if not labels_only:
                    input, _ = self._to_features(paper, vocab, args.render_size)
                lbl = self._annots_to_labels(paper, annot, args.render_size, args.debug)
                if labels_only:
                    yield lbl
                else:
                    yield input, lbl

        if args.debug:
            next(gen())
            exit(0)

        n_classes = len(self.class_.labels) + 1
        n_features = 3

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

        dataset = (
            tf.data.Dataset.from_generator(
                gen,
                ((tf.float32, tf.int32), tf.float32),
                (
                    (
                        tf.TensorShape((None, args.render_size, args.render_size, n_features)),
                        tf.TensorShape((None, args.render_size, args.render_size)),
                    ),
                    tf.TensorShape((None, args.render_size, args.render_size, n_classes)),
                ),
            )
            .prefetch(4)
            .shuffle(buffer_size=4)
            .flat_map(lambda x, y: tf.data.Dataset.from_tensor_slices((x, y)))
            .shuffle(buffer_size=30)
            .batch(args.batch_size)
        )

        print(f"Training CNN ! {len(documents)}")
        self.model.train(dataset, class_weights, n_features, name=self.name, **vars(args))
