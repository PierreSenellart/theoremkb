from abc import abstractmethod
from collections import Counter
from typing import List, Dict, Tuple, Iterator
import os
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn_crfsuite import metrics
from tqdm import tqdm
import pandas as pd
from lxml import etree as ET
from copy import copy, error
from sklearn import preprocessing
from sys import getsizeof
import numpy as np
import pickle
from keras.preprocessing.text import Tokenizer
import tensorflow as tf
import scipy.misc
import imageio

from . import Extractor, TrainableExtractor
from ..classes import AnnotationClass
from ..annotations import AnnotationLayer
from ..paper import AnnotationLayerInfo, Paper
from ..misc.bounding_box import BBX, LabelledBBX
from ..misc.namespaces import *
from ..models import CNNTagger

BATCH_SIZE = 2
DEBUG_CNN  = False

class CNNExtractor(TrainableExtractor):
    """Extracts annotations using a CNN."""

    model: CNNTagger

    @property
    def name(self):
        return self._name

    @property
    def class_(self):
        return self._class_

    @property
    def is_trained(self) -> bool:
        pass

    def __init__(
        self, name: str, class_: AnnotationClass, prefix: str
    ) -> None:
        """Create the feature extractor."""
        self._name = name
        self._class_ = class_

        os.makedirs(f"{prefix}/models", exist_ok=True)

        self.model = CNNTagger(f"{prefix}/models/{class_.name}.{name}.cnn",self._class_.labels)
        """CRF instance."""
        #try:
        #    with open(f"{prefix}/models/{class_.name}.{name}.tokenizer", "rb") as f:
        #        self.tokenizer = pickle.load(f)
        #except:
        #    print("Warning: untrained tokenizer.")
        #    self.tokenizer = Tokenizer(num_words=1000)

    def _to_features(self, paper: Paper) -> np.ndarray:
        #raw_features = paper._build_features()
        images       = paper.render(height=768) # we assume that image is in portrait, fit in 768*768 ~ 600K pixels
        image_channels = images[0].shape[2]

        n_features   = image_channels# + sum(len(features.columns) for features in raw_features.values())
        input_vector = np.zeros((len(images),768,768,n_features))

        for i, image in enumerate(images):
            shape = image.shape
            input_vector[i,:shape[0],:shape[1],:image_channels] = image/255.

        # For now, let's not use any other features than RGB.
        #end_features_index = image_channels
        #for kind, features in raw_features.items():
        #    if kind == f"{ALTO}Page": # pass whole-page features.
        #        continue
        #    
        #    if kind == f"{ALTO}TextLine":
        #        features = features.drop(columns=["first_word", "second_word", "last_word", "first_pattern", "second_pattern", #"last_pattern"], errors="ignore")
        #    
        #    print(">>", kind)
        #    numeric_features = features.select_dtypes(include=["bool", "number"])
        #    word_features    = features.select_dtypes(exclude=["bool", "number"])
        #
        #    print(numeric_features.dtypes, word_features.dtypes)
        #
        #
        #    tokens = root.findall(f".//{kind}")
        #
        #    start_features_index = end_features_index
        #    end_features_index   = start_features_index + len(features.columns)
        #
        #    for i, token in enumerate(tokens):
        #        box = BBX.from_element(token)
        #        #input_vector[box.page_num-1,int(box.min_v):int(box.max_v),int(box.min_h):int(box.max_h),#start_features_index:end_features_index] = features[i]

        return input_vector

    def _annots_to_labels(self, paper: Paper, layer: AnnotationLayerInfo) -> np.ndarray:
        ans = np.zeros((paper.n_pages,768,768,len(self._class_.labels)+1))
        ans[:,:,:,0] = 1

        label_to_index = {v: k+1 for k,v in enumerate(self._class_.labels)}

        annotations = paper.get_annotation_layer(layer.id)
        for bbx in annotations.bbxs.values():
            ans[bbx.page_num-1,int(bbx.min_v):int(bbx.max_v),int(bbx.min_h):int(bbx.max_h),0]     = 0
            label = label_to_index.get(bbx.label, 0)
            ans[bbx.page_num-1,int(bbx.min_v):int(bbx.max_v),int(bbx.min_h):int(bbx.max_h),label] = 1

        return ans


    def _labels_to_annots(self, paper: Paper, labels_by_page: Iterator[np.ndarray]) -> AnnotationLayer:
        res = AnnotationLayer()

        root = paper.get_xml().getroot()
        pages = list(root.findall(f".//{ALTO}Page"))

        for page, labels in zip(pages, labels_by_page):

            if DEBUG_CNN:
                if not os.path.exists("/tmp/tkb"):
                    os.mkdir("/tmp/tkb")
                for i,ft in enumerate(self._class_.labels):
                    imageio.imwrite(f"/tmp/tkb/{paper.id}-{ft}.png", labels[:,:,i+1])
                imageio.imwrite(f"/tmp/tkb/{paper.id}-O.png", labels[:,:,0])

            for token in page.findall(f".//{ALTO}String"):
                box     = BBX.from_element(token)
                slice   = labels[int(box.min_v):int(box.max_v),int(box.min_h):int(box.max_h)]

                votes   = np.sum(slice, axis=(0,1))
                
                label_id = np.argmax(votes)
                if label_id != 0:
                    label = self._class_.labels[label_id-1]
                else:
                    label = 'O'
                res.add_box(LabelledBBX.from_bbx(box,label,0))

        return res


    def apply(self, paper: Paper) -> AnnotationLayer:
        input_vector = self._to_features(paper)

        def labels_generator():
            for i in range(0, len(input_vector), BATCH_SIZE):
                tagged_images = self.model(input_vector[i:i+BATCH_SIZE])

                for j in range(tagged_images.shape[0]):
                    yield tagged_images[j]
        

        return self._labels_to_annots(paper, labels_generator())



    def info(self):
        pass

    def train(
        self,
        documents: List[Tuple[Paper, AnnotationLayerInfo]],
        verbose=False,
    ):
        def gen():
            nonlocal documents
            for paper, annot in documents:
                ft  = self._to_features(paper)
                lbl = self._annots_to_labels(paper, annot)
                for i in range(ft.shape[0]):
                    yield ft[i],lbl[i]

        n_classes = len(self._class_.labels) + 1
        n_features = 3
        #class_weights = {k: 0 for k in range(n_classes)}
        #tot = 0
        #for _,lbl in gen():
        #    for i in range(n_classes):
        #        v = np.sum(lbl[:,:,i])
        #        class_weights[i] += v
        #        tot += v
        #class_weights = {k: v/tot for k,v in class_weights.items()}
        class_weights = {0: 0.5498216987038238, 1: 0.0007099176293894675, 2: 0.0, 3: 0.01285532526904739, 4: 0.0019027098170397146, 5: 0.003662149242459911, 6: 0.3737182933705505, 7: 0.030561784907767467, 8: 0.0009232245488616031, 9: 0.02584489651106011}

        class_weights = {k: 1/v if v != 0 else 0 for k,v in class_weights.items()}
        tot = sum(class_weights.values())
        class_weights = {k: v/tot for k,v in class_weights.items()}
        
        dataset = tf.data.Dataset.from_generator(gen, (tf.float32, tf.float32), (tf.TensorShape((768,768,n_features)),tf.TensorShape((768,768,n_classes))))
        dataset = dataset.batch(BATCH_SIZE)

        self.model.train(dataset, class_weights)
