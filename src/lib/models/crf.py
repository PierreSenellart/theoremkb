from sklearn_crfsuite import CRF
from collections import Counter
import pickle
import os, time
from termcolor import colored
from typing import Dict, Any, List, Iterator


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
            with open(self.model_filename, "rb") as f:
                self.model = pickle.load(f)
        else:
            self.model = None

    def reset(self, args):
        self.model = CRF(c1=args.c1, c2=args.c2, max_iterations=args.max_iter, verbose=args.verbose, min_freq=args.min_freq) 

    def __call__(self, tokens: Iterator[List[dict]]):
        if self.model is None:
            raise Exception("Model not trained")
        return self.model.predict(tokens)

    @property
    def is_trained(self):
        return self.model is not None and self.model.state_features_ is not None

    def train(
        self,
        tokens: Iterator[List[dict]],
        labels: Iterator[List[str]],
        args,
        val_tokens=None,
        val_labels=None,
    ):
        self.reset(args)
        t0 = time.time()

        self.model.fit(tokens, labels, val_tokens, val_labels)

        if args.verbose:
            print(f"Took {time.time() - t0}s to train.")
            print("Saved CRF.")
        with open(self.model_filename, "wb") as f:
            pickle.dump(self.model, f)

    def description(self):
        if self.model is None:
            return """untrained."""
        else:
            return f"""
            C1:         {self.model.c1}
            C2:         {self.model.c2}
            MIN-FREQ:   {self.model.min_freq}
            MAX-ITER:   {self.model.max_iterations}
            """

    def info(self):
        print("Top likely transitions:")
        print_transitions(Counter(self.model.transition_features_).most_common(20))

        print("Top positive:")
        by_label: Dict[str, Dict[str, Any]] = {}
        for (feature, label), value in self.model.state_features_.items():
            if label not in by_label:
                by_label[label] = {}
            by_label[label][feature] = value

        for label, ft in sorted(by_label.items()):
            print("##", colored(label, "red"))
            state_features = Counter(ft).most_common(20)
            for feature, weight in state_features:
                print(" %0.6f %s" % (weight, feature))
            state_features = Counter(ft).most_common()[:-20:-1]
            for feature, weight in state_features:
                print(" %0.6f %s" % (weight, feature))
