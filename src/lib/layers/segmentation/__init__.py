from lxml import etree as ET
from collections import namedtuple
from typing import List, Dict, Tuple
from tqdm import tqdm
import os

from ...annotations import AnnotationLayer
from ...paper import AnnotationLayerInfo, Paper
from ...misc.bounding_box import BBX, LabelledBBX
from .. import Layer 
from ...misc.namespaces import *
from ...features import FeatureExtractor
from ...features.String import StringFeaturesExtractor
from ...models import CRFTagger


segmentation_schema = {
    "type": "object",
    "properties": {
        "label": {
            "type": "string",
            "enum": ["titlePage", "front", "headnote", "footnote", "body", "listBibl", "page", "annex"],
            "enumNames": ["Cover page", "Document header", "Page header", "Page footer", "Body", "Bibliographical section", "Page number", "Annex"]
        }
        
    },
    "required": "label"
}

class SegmentationFeaturesExtractor(FeatureExtractor):
    
    string_extractor: StringFeaturesExtractor

    def __init__(self, root: ET.Element):
        self.string_extractor = StringFeaturesExtractor(root)

    def has(self, tag: str) -> bool:
        return tag in [f"{ALTO}String"]

    def get(self, element: ET.Element) -> dict:
        if element.tag == f"{ALTO}String":
            return self.string_extractor.get(element)
        else:
            raise KeyError

    def stop_at(self, tag: str) -> bool:
        return tag in [f"{ALTO}String"]
    


class SegmentationLayer(Layer):
    model: CRFTagger

    def __init__(self, prefix):
        super().__init__("segmentation", segmentation_schema)

        os.makedirs(f"{prefix}/models", exist_ok=True)
        self.model = CRFTagger(f"{prefix}/models/segmenter.crf") # todo: not hardcode addr


    def apply(self, paper: Paper) -> AnnotationLayer:
        xml = paper.get_xml()
        xml_root = xml.getroot()
        
        output_accumulator = []
        SegmentationFeaturesExtractor(xml_root).extract_features(output_accumulator, xml_root)

        tokens, features = zip(*output_accumulator)
        
        labels = self.model(features)

        # update XML, merging neighboring nodes with same label.
        result = AnnotationLayer()
        previous_label = ""
        counter = 0
        for node, label in zip(tokens, labels):
            # remove B/I format.
            if label.startswith("B-") or label.startswith("I-"):
                label = label[2:]
            
            if label != previous_label:
                counter += 1
            
            result.add_box(LabelledBBX.from_bbx(BBX.from_element(node), label, counter))

            previous_label = label

        return result

    def train(self, documents: List[Tuple[Paper, AnnotationLayerInfo]]): 
        X = []
        y = []

        for paper, layer in documents:
            xml_root = paper.get_xml().getroot()
            annotation_layer = paper.get_annotation_layer(layer.id)
            
            output_accumulator = []
            SegmentationFeaturesExtractor(xml_root).extract_features(output_accumulator, xml_root)

            tokens, features = zip(*output_accumulator)

            # convert labels to B/I format.
            target = []
            features_normalized = []
            last_label = None
            for i, token in enumerate(tokens):
                label = annotation_layer.get_label(BBX.from_element(token))
                if label == last_label:
                    target.append("I-"+label)
                else:
                    target.append("B-"+label)
                last_label = label

                
            
            X.append(features_normalized)
            y.append(target)

        self.model.train(X, y)