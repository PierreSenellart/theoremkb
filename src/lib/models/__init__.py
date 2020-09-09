from ..config import ENABLE_TENSORFLOW

from .crf import CRFTagger

if ENABLE_TENSORFLOW:
    from .cnn import CNNTagger
    from .cnn1d import CNN1DTagger
