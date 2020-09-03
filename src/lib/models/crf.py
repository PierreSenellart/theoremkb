from sklearn_crfsuite import CRF
from collections import Counter
import pickle
import os, time
from termcolor import colored
from typing import Dict, Any, List

def print_transitions(trans_features):
    for (label_from, label_to), weight in trans_features:
        print("%-6s -> %-7s %0.6f" % (label_from, label_to, weight))


def print_state_features(state_features):
    for (attr, label), weight in state_features:
        print("%0.6f %-8s %s" % (weight, label, attr))


class CRFTagger:
    model: CRF
    model_filename: str

    def __init__(self, model_filename):
        self.model_filename = model_filename

        if os.path.exists(model_filename):
            print("Loading CRF.")
            with open(self.model_filename, "rb") as f:
                self.model = pickle.load(f)
        else:
            print("Warning: untrained CRF.")
            self.reset()

    def reset(self):
        self.model = CRF(c1=1.0, c2=1.0, max_iterations=200)

    def __call__(self, tokens: List[List[dict]]):
        return self.model.predict(tokens)

    @property
    def is_trained(self):
        return self.model.state_features_ is not None

    def train(self, tokens: List[List[dict]], labels: List[List[str]], verbose=False):
        assert len(tokens) == len(list(labels))
        self.reset()
        t0 = time.time()
        self.model.fit(tokens, labels)

        if verbose:
            print(f"Took {time.time() - t0}s to train.")
            print("Saved CRF.")
        with open(self.model_filename, "wb") as f:
            pickle.dump(self.model, f)

    def info(self):
        print("Top likely transitions:")
        print(self.model.transition_features_)
        print_transitions(Counter(self.model.transition_features_).most_common(20))

        print("Top positive:")
        by_label: Dict[str, Dict[str, Any]] = {}
        for (feature, label), value in self.model.state_features_.items():
            if label not in by_label:
                by_label[label] = {}
            by_label[label][feature] = value
        
        for label, ft in sorted(by_label.items()):
            print("##", colored(label, 'red'))
            state_features = Counter(ft).most_common(6)
            for feature, weight in state_features:
                print(" %0.6f %s" % (weight, feature))
            
            
