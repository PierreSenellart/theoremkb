from abc import abstractmethod
from typing import List, Tuple, Optional
import os
from sklearn_crfsuite import metrics
from tqdm import tqdm
from sys import getsizeof
from joblib import Parallel, delayed
import joblib
import argparse
import itertools
import threading

from . import Extractor, TrainableExtractor
from ..classes import AnnotationClass
from ..annotations import AnnotationLayer
from ..paper import AnnotationLayerInfo, Paper
from ..misc.bounding_box import BBX, LabelledBBX
from ..misc.namespaces import *
from ..models import CRFTagger

class Parallel(joblib.Parallel):
    def it(self, iterable):
        try:
            t = threading.Thread(target=self.__call__, args=(iterable,))
            t.start()

            i = 0
            output = self._output
            while t.is_alive() or (output and i < len(output)):
                # catch the list reference and store before it's overwritten
                if output is None:
                    output = self._output
                # yield when a new item appears
                if output and i < len(output):
                    yield output[i]
                    i += 1
        finally:
            t.join()


class CRFExtractor(TrainableExtractor):
    """Extracts annotations using a linear-chain CRF."""

    model: Optional[CRFTagger]
    name: str
    target: str
    class_: AnnotationClass

    @property
    def is_trained(self) -> bool:
        self._load_model()
        return self.model.is_trained

    @property
    def description(self) -> str:
        self._load_model()
        descr = f"CRFExtractor ({self.class_.name}) -> {self.target.split('}')[1]}\n"
        return descr + self.model.description()

    def info(self):
        self.model.info()

    def __init__(
        self, 
        prefix: str, 
        name: str, 
        class_: AnnotationClass, 
        target: str,
    ) -> None:
        """Create the feature extractor."""

        os.makedirs(f"{prefix}/models", exist_ok=True)

        self.prefix = prefix
        self.model  = None
        self.name   = name+".crf"
        self.class_ = class_
        self.target = target
        """CRF instance."""

    def _load_model(self):
        if self.model is None:
            self.model = CRFTagger(f"{self.prefix}/models/{self.class_.name}.{self.name}.crf")

    def apply(self, paper: Paper, parameters: List[str]) -> AnnotationLayer:
        self._load_model()

        leaf_node   = self.target
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
            # remove B/I/E format.
            if label.startswith("B-") or label.startswith("I-") or label.startswith("E-"):
                label = label[2:]

            if label == "O":
                continue

            if label != previous_label:
                counter += 1

            result.add_box(LabelledBBX.from_bbx(bbx, label, counter))

            previous_label = label

        return result

    @classmethod
    def parse_args(cls, parser: argparse.ArgumentParser):
        parser.add_argument("--only", nargs="*", type=str)
        parser.add_argument("--balance", action="store_true")
        parser.add_argument("--c1", type=float, default=0.1)
        parser.add_argument("--c2", type=float, default=0.1)
        parser.add_argument("--max-iter", type=int, default=500)
        parser.add_argument("--verbose", default=False, action="store_true")
        parser.add_argument("--min-freq", type=int, default=1)
        
    def train(
        self,
        documents: List[Tuple[Paper, AnnotationLayerInfo]],
        args,
        verbose=False,
    ):
        self._load_model()
        self.model.reset(args)
        print(self.description)

        if args.only is not None:
            only = set(self.class_.labels).intersection(args.only)
            if len(only) != len(set(args.only)):
                print("Some filtered labels are not part of the allowed labels:", set(args.only).difference(self.class_.labels))
                print("Allowed labels are:", set(self.class_.labels))
                exit(1)
        else:
            only = None


        def featurize(paper, layer, balance=False):
            annotations = paper.get_annotation_layer(layer.id)
            
            leaf_node   = self.target
            tokens      = paper.get_xml().getroot().findall(f".//{leaf_node}")
            labels      = [annotations.get_label(BBX.from_element(token)) for token in tokens]

            target       = []
            target_idx   = set() 
            block_count  = 0

            for i, label in enumerate(labels):
                if only is not None:
                    if label not in only:
                        label = "O"

                if label == "O":
                    target.append("O")
                elif i > 0 and label != labels[i-1]:
                    target_idx.add(i)
                    block_count += 1
                    target.append("B-" + label)
                elif i < len(labels) - 1 and label != labels[i+1]:
                    target_idx.add(i)
                    target.append("E-" + label)
                else:
                    target_idx.add(i)
                    target.append("I-" + label)
                last_label = label

            if balance:
                if block_count == 0:
                    return None
                    
                context_size = 2*len(target_idx) // block_count
                
                for i in list(target_idx):
                    target_idx.update(range(max(0,i-context_size),min(i+context_size,len(labels)-1)))
                target_idx_lst = list(target_idx)
                target_idx_lst.sort()

                features    = paper.get_features(leaf_node).iloc[target_idx_lst].to_dict('records')
                target      = [target[i] for i in target_idx_lst]
    
            else:
                features    = paper.get_features(leaf_node).to_dict('records')

            return features, target, paper.id

        def create_feature_generators(dataset):
            features_gen   = filter(lambda x: x is not None, Parallel(n_jobs=-1).it(delayed(featurize)(paper,layer,args.balance) for paper,layer in tqdm(dataset)))
            features_gen_3 = itertools.tee(features_gen, 3)

            return (x[0] for x in features_gen_3[0]), (x[1] for x in features_gen_3[1]), (x[2] for x in features_gen_3[2])

        X,y,ids             = create_feature_generators(documents)
        if verbose:
            print("Starting training.")

        self.model.train(X, y, args)
