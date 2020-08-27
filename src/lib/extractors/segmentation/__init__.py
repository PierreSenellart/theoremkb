from .crf import SegmentationExtractor as SegmentationCRFExtractor
from .crf import SegmentationStringExtractor as SegmentationStringCRFExtractor
from ..cnn import CNNExtractor
from ...classes import SegmentationAnnotationClass



class SegmentationCNNExtractor(CNNExtractor):
    def __init__(self, prefix):
        super().__init__("cnn", SegmentationAnnotationClass(), prefix)
