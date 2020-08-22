from __future__ import annotations
from typing import Dict, Optional, List, Tuple
from enum import Enum
import os
import shutil
import subprocess
import pickle
import shortuuid
from lxml import etree as ET
from dataclasses import dataclass
import time
import pandas as pd, numpy as np
from sklearn import preprocessing

from .features import get_feature_extractors

from .classes import AnnotationClassFilter
from .config import DATA_PATH, REBUILD_FEATURES
from .annotations import AnnotationLayer
from .misc.bounding_box import BBX, LabelledBBX
from .misc.namespaces import *
from .misc import remove_prefix


def _standardize(features: pd.DataFrame) -> pd.DataFrame:
    """Perform document-wide normalization on numeric features

    Args:
        features (List[dict]): list of features. 

    Returns:
        List[dict]: list of normalized features.
    """
    numeric_df = features.select_dtypes(include='number')
    boolean_df = features.select_dtypes(include='bool')
    other_df   = features.select_dtypes(exclude=['number', 'bool'])

    normalized_numerics = preprocessing.scale(numeric_df)
    normalized_df = pd.DataFrame(normalized_numerics, columns=numeric_df.columns)
    boolean_df = 2 * boolean_df.astype('float') - 1
    
    return pd.concat([boolean_df, normalized_df, other_df], axis=1)

def _add_deltas(features: pd.DataFrame, to_drop: Optional[str]) -> pd.DataFrame:
    numeric_features = features.select_dtypes(include='number')
    
    if to_drop:
        numeric_features.drop(to_drop, axis=1, inplace=True)
    numeric_features_next = numeric_features.diff(periods=-1).add_suffix("_next")
    numeric_features_prev = numeric_features.diff(periods=1).add_suffix("_prev")
    return pd.concat([features, numeric_features_next, numeric_features_prev], axis=1)

@dataclass
class AnnotationLayerInfo:
    """ Annotation layer metadata """

    id: str
    name: str
    class_: str
    training: bool

    def to_web(self, paper_id: str) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "training": self.training,
            "class": self.class_,
            "paperId": paper_id,
        }


class ParentModelNotFoundException(Exception):
    kind: str

    def __init__(self, kind):
        self.kind = kind

    def __str__(self):
        return "Parent model not found: " + self.kind

ALTO_HIERARCHY = [ 
    f"{ALTO}Page",
    f"{ALTO}PrintSpace",
    f"{ALTO}TextBlock",
    f"{ALTO}TextLine",
    f"{ALTO}String"
]
class Paper:

    id: str
    pdf_path: str
    metadata_directory: str

    layers: Dict[str, AnnotationLayerInfo]

    def __init__(self, id: str, pdf_path: str, layers={}) -> None:
        self.id = id
        self.pdf_path = pdf_path
        self.layers = layers

        self.metadata_directory = DATA_PATH + "/papers/" + id
        if os.path.exists(self.metadata_directory):
            shutil.rmtree(self.metadata_directory)
        os.makedirs(self.metadata_directory)

    def has_training_layer(self, class_: str) -> bool:
        for layer in self.layers.values():
            if layer.class_ == class_ and layer.training:
                return True
        return False

    def get_training_layer(self, class_: str) -> Optional[AnnotationLayerInfo]:
        for layer in self.layers.values():
            if layer.class_ == class_ and layer.training:
                return layer
        return None

    def get_best_layer(self, class_: str) -> Optional[AnnotationLayerInfo]:
        best_layer = None
        for layer in self.layers.values():
            if layer.class_ == class_ and layer.training:
                return layer
            elif layer.class_ == class_:
                best_layer = layer
        return best_layer

    def get_annotation_layer(self, layer_id: str) -> AnnotationLayer:
        location = f"{self.metadata_directory}/annot_{layer_id}.json"
        return AnnotationLayer(location)

    def remove_annotation_layer(self, layer_id: str):
        location = f"{self.metadata_directory}/annot_{layer_id}.json"
        try:
            os.remove(location)
        except Exception:
            print("exception when deleted: ", location)
            pass
        del self.layers[layer_id]

    def add_annotation_layer(
        self, meta: AnnotationLayerInfo, content: Optional[AnnotationLayer] = None
    ) -> AnnotationLayer:
        location = f"{self.metadata_directory}/annot_{meta.id}.json"
        # todo: check that id is not already in use.
        self.layers[meta.id] = meta
        if content is None:
            return AnnotationLayer(location)
        else:
            content.location = location
            content.save()
            return content

    def get_annotation_meta(self, layer_id: str) -> AnnotationLayerInfo:
        return self.layers[layer_id]

    def __pdfalto(self, xml_path):
        result = subprocess.run(
            [
                "pdfalto",
                "-readingOrder",
                "-blocks",
                "-annotation",
                self.pdf_path,
                xml_path,
            ]
        )
        if result.returncode != 0:
            raise Exception("Failed to convert to xml.")

    def get_xml(self) -> ET.ElementTree:
        xml_path = f"{self.metadata_directory}/article.xml"
        if not os.path.exists(xml_path):
            self.__pdfalto(xml_path)

        with open(xml_path, "r") as f:
            return ET.parse(f)

    def get_pdf_annotations(self) -> AnnotationLayer:
        xml_path = f"{self.metadata_directory}/article.xml"
        xml_annot_path = f"{self.metadata_directory}/article_annot.xml"
        if not os.path.exists(xml_annot_path):
            self.__pdfalto(xml_path)

        with open(xml_annot_path, "r") as f:
            xml_annot = ET.parse(f)
            return AnnotationLayer.from_pdf_annotations(xml_annot)

    def apply_annotations_on(
        self,
        annotations: AnnotationLayer,
        target: str,
        only_for: List[AnnotationClassFilter] = [],
    ) -> AnnotationLayer:
        layer = AnnotationLayer()

        req_layers = {x.name: self.get_best_layer(x.name) for x in only_for}
        for k, v in req_layers.items():
            if v is None:
                raise ParentModelNotFoundException(k)

        req_layers = {k: self.get_annotation_layer(v.id) for k, v in req_layers.items()}

        for child in self.get_xml().findall(f".//{target}"):
            bbx = BBX.from_element(child)

            ok = False
            if only_for == []:
                ok = True
            else:
                for p in only_for:
                    if req_layers[p.name].get_label(bbx) in p.labels:
                        ok = True
                        break

            if ok:
                box = annotations.get(bbx, mode="full")
                if box:
                    layer.add_box(LabelledBBX.from_bbx(bbx, box.label, box.group, box.user_data))

        return layer

    def extract_raw_text(self, annotations: AnnotationLayer, target: str) -> str:
        result = []

        for child in self.get_xml().findall(f".//{target}"):
            bbx = BBX.from_element(child)
            if annotations.get_label(bbx, mode="full") != "O":
                result.append(child.get("CONTENT"))

        return " ".join(result)

    def to_web(self, classes: List[str]) -> dict:
        class_status = {k: {"training": False, "count": 0} for k in classes}
        for layer in self.layers.values():
            if layer.training:
                class_status[layer.class_]["training"] = True
            class_status[layer.class_]["count"] += 1

        header_annot_info = self.get_best_layer("header")
        title = ""

        if header_annot_info is not None:
            header_annot = self.get_annotation_layer(header_annot_info.id)
            header_annot.filter(lambda x: x == "title")
            title = self.extract_raw_text(header_annot, f"{ALTO}String")

        return {
            "id": self.id,
            "pdf": f"/papers/{self.id}/pdf",
            "classStatus": class_status,
            "title": title,
        }

    def _build_features(self) -> Dict[str, pd.DataFrame]:
        df_path = f"{self.metadata_directory}/features.pkl"

        if os.path.exists(df_path) and not REBUILD_FEATURES:
            with open(df_path, 'rb') as f:
                return pickle.load(f)
        else:
            xml = self.get_xml().getroot()
            feature_extractors = get_feature_extractors(xml)

            features_by_node = {k: [] for k in feature_extractors.keys()}
            indices          = {k: 0 for k in feature_extractors.keys()}

            ancestors = []

            def dfs(node: ET.Element):
                nonlocal ancestors, indices
                if node.tag in features_by_node:
                    ancestors.append(node.tag)
                    indices[node.tag] += 1

                    features_by_node[node.tag].append(feature_extractors[node.tag].get(node))
                    if len(ancestors) > 1:
                        features_by_node[node.tag][-1][ancestors[-2]] = indices[ancestors[-2]]-1
                    
                for children in node:
                    dfs(children)

                if node.tag in features_by_node:
                    ancestors.pop()

            dfs(xml)

            features_dict = {k: pd.DataFrame.from_dict(v) for k,v in features_by_node.items()}
            with open(df_path, 'wb') as f:
                pickle.dump(features_dict, f)
            return features_dict

    def get_features(self, leaf_node: str, standardize: bool=True) -> pd.DataFrame:
        """
        Generate features for each kind of token in PDF XML file.
        """
        
        features_dict = self._build_features()

        for k,v in features_dict.items():
            to_drop = None
            idx = ALTO_HIERARCHY.index(k)
            for p in reversed(ALTO_HIERARCHY[:idx]):
                if p in features_dict:
                    to_drop = p
                    break
            print(k, to_drop)
            features_dict[k] = _add_deltas(v, to_drop)

        try:
            leaf_index = ALTO_HIERARCHY.index(leaf_node)
        except ValueError:
            raise Exception("Could not find requested leaf node in the xml hierarchy.")

        prefix = ""
        result_df: Optional[pd.DataFrame] = None

        for index,node in reversed(list(enumerate(ALTO_HIERARCHY))):
            if node in features_dict:
                old_prefix = prefix

                if result_df is None:
                    prefix     = remove_prefix(node)+"."
                    result_df = features_dict[node].add_prefix(prefix)
                else:
                    if index >= leaf_index:
                        result_df = result_df.groupby(by=old_prefix+node).agg(['min', 'max', 'std', 'mean'])
                        result_df.columns = result_df.columns.map('_'.join)
                    
                    prefix = remove_prefix(node)+"."
                    target = features_dict[node].add_prefix(prefix)
                    result_df = result_df.join(target, on=old_prefix+node)
                    
                    if old_prefix+node in result_df.columns:
                        result_df = result_df.drop(old_prefix+node, axis=1)
        result_df.index.name = NotImplemented
        
        if standardize:
            return _standardize(result_df).fillna(0)
        else:
            return result_df.fillna(0)
