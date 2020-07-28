
from sklearn_crfsuite import CRF
from collections import Counter
import pickle
import os

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
            self.model = CRF()

    def __call__(self, tokens):
        return self.model.predict_single(tokens)

    def train(self, tokens, labels):
        print(len(tokens))
        print(len(labels))
        assert len(tokens) == len(list(labels))
        self.model.fit(tokens, labels)
        print("Saved CRF.")
        with open(self.model_filename, "wb") as f:
            pickle.dump(self.model, f)

        print("Top likely transitions:")
        print_transitions(
            Counter(self.model.transition_features_).most_common(20))

        print("Top positive:")
        print_state_features(
            Counter(self.model.state_features_).most_common(20))