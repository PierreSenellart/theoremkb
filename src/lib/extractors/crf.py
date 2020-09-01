from abc import abstractmethod
from typing import List, Tuple, Optional
import os
from sklearn.model_selection import train_test_split
from sklearn_crfsuite import metrics
from tqdm import tqdm
from sys import getsizeof
from joblib import Parallel, delayed

from . import Extractor, TrainableExtractor
from ..classes import AnnotationClass
from ..annotations import AnnotationLayer
from ..paper import AnnotationLayerInfo, Paper
from ..misc.bounding_box import BBX, LabelledBBX
from ..misc.namespaces import *
from ..models import CRFTagger

MAX_DOCS = None

class CRFExtractor(TrainableExtractor):
    """Extracts annotations using a linear-chain CRF."""

    model: Optional[CRFTagger]

    @property
    def is_trained(self) -> bool:
        return self.model.is_trained

    def __init__(
        self, prefix: str
    ) -> None:
        """Create the feature extractor."""

        os.makedirs(f"{prefix}/models", exist_ok=True)

        self.prefix = prefix
        self.model = None
        """CRF instance."""

    def _load_model(self):
        if self.model is None:
            self.model = CRFTagger(f"{self.prefix}/models/{self.class_.name}.{self.name}.crf")

    @abstractmethod
    def get_leaf_node(self) -> str:
        """Get the leaf node."""

    def apply(self, paper: Paper) -> AnnotationLayer:
        self._load_model()

        leaf_node   = self.get_leaf_node()
        tokens      = list(paper.get_xml().getroot().findall(f".//{leaf_node}"))
        features    = paper.get_features(leaf_node).to_dict('records')

        box_validator = paper.get_box_validator(self.class_)

        filtered_tokens     = []
        filtered_features   = []
        for node, ft in zip(tokens, features):
            bbx = BBX.from_element(node)
            if box_validator(bbx):
                filtered_tokens.append(bbx)
                filtered_features.append(ft)


        labels      = self.model([filtered_features])[0]
        #print("Apply:")
        #print(Counter(labels))

        result = AnnotationLayer()
        previous_label, counter = "", 0

        for bbx, label in zip(filtered_tokens, labels):
            # remove B/I format.
            if label.startswith("B-") or label.startswith("I-"):
                label = label[2:]

            if label == "O":
                continue

            if label != previous_label:
                counter += 1

            result.add_box(LabelledBBX.from_bbx(bbx, label, counter))

            previous_label = label

        return result

    def info(self):
        print("Model: ")
        self._load_model()
        self.model.info()

    def train(
        self,
        documents: List[Tuple[Paper, AnnotationLayerInfo]],
        settings: List[str]=[],
        verbose=False,
    ):
        print("Preparing documents..")
        self._load_model()

        if MAX_DOCS is not None:
            documents = documents[:MAX_DOCS]

        def featurize(paper, layer):
            annotations      = paper.get_annotation_layer(layer.id)
            
            leaf_node   = self.get_leaf_node()
            tokens      = list(paper.get_xml().getroot().findall(f".//{leaf_node}"))
            features    = paper.get_features(leaf_node).to_dict('records')

            target = []
            last_label = None
            for token in tokens:
                label = annotations.get_label(BBX.from_element(token))
                if label != last_label:
                    target.append("B-" + label)
                else:
                    target.append("I-" + label)
                last_label = label

            return features, target, paper.id

        X,y,ids = zip(*Parallel(n_jobs=-1)(delayed(featurize)(paper,layer) for paper,layer in tqdm(documents)))

        X_train, X_test, y_train, y_test, ids_train, ids_test = train_test_split(
            X, y, ids, test_size=0.10, random_state=1
        )
        print("Train/test:", ids_train, "/", ids_test)
        self.model.train(X_train, y_train, verbose=True)
        # evaluate performance.
        y_test_pred = self.model(X_test)
        y_train_pred = self.model(X_train)

        labels = list(self.model.model.classes_)

        # group B and I results
        sorted_labels = sorted(labels, key=lambda name: (name[1:], name[0]))
        print("# Test:")
        print(
            metrics.flat_classification_report(
                y_test, y_test_pred, labels=sorted_labels, digits=3
            )
        )
        print("# Train:")
        print(
            metrics.flat_classification_report(
                y_train, y_train_pred, labels=sorted_labels, digits=3
            )
        )

class CRFFeatureExtractor(Extractor):

    @property
    def name(self):
        return self._name

    @property
    def class_(self):
        return self._class_

    def __init__(self, extractor: CRFExtractor) -> None:
        """Create the feature extractor."""
        self._name = extractor.name+".ft"
        self._class_ = extractor.class_
        self._parent = extractor

    def apply(self, paper: Paper) -> AnnotationLayer:

        leaf_node   = self._parent.get_leaf_node()
        tokens      = list(paper.get_xml().getroot().findall(f".//{ALTO}TextBlock"))
        features    = paper.get_features(leaf_node, standardize=False).to_dict('records')

        result = AnnotationLayer()

        for counter, (token, ft) in enumerate(zip(tokens, features)):
            ft_hiearch = {}
            for k,v in ft.items():
                a,b = k.split(".", 1)
                if a not in ft_hiearch:
                    ft_hiearch[a] = {}
                ft_hiearch[a][b] = v

            result.add_box(LabelledBBX.from_bbx(BBX.from_element(token), "", counter, user_data=ft_hiearch))
        return result
        
