

from abc import abstractmethod
from lxml import etree as ET
from collections import namedtuple, Counter
from typing import List, Dict, Tuple
from tqdm import tqdm
import os
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn_crfsuite import scorers
from sklearn_crfsuite import metrics
from sklearn.metrics import confusion_matrix

from . import TrainableExtractor
from ..annotations import AnnotationLayer
from ..paper import AnnotationLayerInfo, Paper
from ..misc.bounding_box import BBX, LabelledBBX
from ..misc.namespaces import *
from ..features import FeatureExtractor
from ..features.String import StringFeaturesExtractor
from ..models import CRFTagger

def _flatten(features: dict) -> dict:
    """Flatten dict of dict

    Transform a multi-stage dictionnary into a flat feature dictionary.

    Args:
        features (dict): a (potentially nested) feature dictionary
    """
    result = {}
    for k,v in features.items():
        if type(v) is dict:
            for k2, v2 in _flatten(v).items():
                result[f"{k}:{k2}"] = v2
        else:
            result[k] = v
    return result
     


def _normalize(features: List[dict]) -> List[dict]:
    """Perform document-wide normalization on numeric features

    Args:
        features (List[dict]): list of features. 

    Returns:
        List[dict]: list of normalized features.
    """
    assert len(features) > 0
    n = len(features)
        
    numeric_features = []
    boolean_features = []
    other_features   = []
    for k,v in features[0].items():
        if type(v) in [int, float]:
            numeric_features.append(k)
        elif type(v) == bool:
            boolean_features.append(k)
        else:
            other_features.append(k)
    
    sum = {k: 0 for k in numeric_features}
    sum_squared  = {k: 0 for k in numeric_features}

    for token in features:
        for k in numeric_features:
            sum[k] += token[k]
            sum_squared[k] += token[k]**2
    
    std = {k: np.sqrt(sum_squared[k]/n - (sum[k]/n)**2) for k in numeric_features}

    result_step_1 = []
    for token in features:
        ft = {}
        for f in numeric_features:
            try:
                if std[f] == 0:
                    ft[f] = 0
                else:
                    ft[f] = (token[f] - sum[f]/len(features))/std[f]
            except KeyError:
                pass
        for f in boolean_features:
            try:
                ft[f] = 2*token[f] - 1
            except KeyError:
                pass
        for f in other_features:
            try:
                ft[f] = token[f]
            except KeyError:
                pass
        result_step_1.append(ft)

    # add prec/next features
    result_step_2 = []
    for i, token in enumerate(result_step_1):
        ft = token

        if i > 0:
            prec_token = result_step_1[i-1]
            for f in numeric_features + boolean_features:
                ft["prec_"+f] = prec_token[f] - token[f]
        if i < n-1:
            next_token = result_step_1[i+1]
            for f in numeric_features + boolean_features:
                ft["next_"+f] = next_token[f] - token[f]
        

        result_step_2.append(ft)

    return result_step_2


class CRFExtractor(TrainableExtractor):
    """Extracts annotations using a linear-chain CRF."""

    model: CRFTagger

    @property
    def name(self):
        return self._name

    @property
    def kind(self):
        return self._kind
    
    @property
    def requirements(self):
        return self._requirements

    @property
    def is_trained(self) -> bool:
        return self.model.is_trained
    
    def __init__(self, name: str, kind: str, requirements: List[str], prefix: str) -> None:
        """Create the feature extractor."""
        self._name = name
        self._kind = kind
        self._requirements = requirements

        os.makedirs(f"{prefix}/models", exist_ok=True)

        self.model = CRFTagger(f"{prefix}/models/{name}.crf")
        """CRF instance."""
    
    @abstractmethod
    def get_feature_extractor(self, paper: Paper, reqs: Dict[str, AnnotationLayer]) -> FeatureExtractor:
        """Get feature extractor."""

    def _featurize(self, paper: Paper, reqs: Dict[str, AnnotationLayer]) -> Tuple[List[str], List[dict]]:
        xml = paper.get_xml()
        xml_root = xml.getroot()

        output_accumulator = []
        self.get_feature_extractor(paper, reqs).extract_features(output_accumulator, xml_root)
        tokens, features = zip(*output_accumulator)
        return list(tokens), _normalize(list(map(_flatten,features)))


    def apply(self, paper: Paper, reqs: Dict[str, AnnotationLayer]) -> AnnotationLayer:
    
        tokens, features = self._featurize(paper, reqs)
        labels = self.model([features])[0]
        print("Apply:")
        print(Counter(labels))

        result = AnnotationLayer()
        previous_label, counter = "", 0

        for node, label in zip(tokens, labels):
            # remove B/I format.
            if label.startswith("B-") or label.startswith("I-"):
                label = label[2:]
            
            if label == "O":
                continue

            if label != previous_label:
                counter += 1
            
            result.add_box(LabelledBBX.from_bbx(BBX.from_element(node), label, counter))

            previous_label = label

        return result
    
    def train(self, documents: List[Tuple[Paper, Dict[str, AnnotationLayer], AnnotationLayerInfo]], verbose=False):
        X = []
        y = []
        ids = []

        for paper, reqs, layer in documents: 
            annotations = paper.get_annotation_layer(layer.id)
            tokens, features = self._featurize(paper, reqs)

            target = []
            #features_normalized = []
            last_label = None
            for token in tokens:
                label = annotations.get_label(BBX.from_element(token))
                if label != last_label:
                    target.append("B-"+label)
                else:
                    target.append("I-"+label)
                last_label = label
        
            X.append(features)
            y.append(target)
            ids.append(paper.id)
        
        X_train, X_test, y_train, y_test, ids_train, ids_test = train_test_split(X, y, ids, test_size=0.5, random_state=0)
        print("Train/test:",ids_train,"/",ids_test)
        self.model.train(X_train, y_train, verbose=True)
        # evaluate performance.
        y_test_pred = self.model(X_test)
        y_train_pred= self.model(X_train)
        
        labels = list(self.model.model.classes_)
        
        # group B and I results
        sorted_labels = sorted(
            labels,
            key=lambda name: (name[1:], name[0])
        )
        print("# Test:")
        print(metrics.flat_classification_report(
            y_test, y_test_pred, labels=sorted_labels, digits=3
        ))
        print("# Train:")
        print(metrics.flat_classification_report(
            y_train, y_train_pred, labels=sorted_labels, digits=3
        ))
