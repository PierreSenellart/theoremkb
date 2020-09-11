from __future__ import annotations
from typing import Dict, Optional, List, Tuple

import os, bz2
import shutil
import subprocess
import pickle
import shortuuid
from lxml import etree as ET
from collections import Counter

import time
import pandas as pd, numpy as np
from sklearn import preprocessing
import time

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy import String, Column, ForeignKey, DateTime, Text
import datetime

import fitz


from .features import get_feature_extractors

from .classes import AnnotationClass
from .config import DATA_PATH, REBUILD_FEATURES, SQL_ENGINE
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
    numeric_df = features.select_dtypes(include="number")
    boolean_df = features.select_dtypes(include="bool")
    other_df = features.select_dtypes(exclude=["number", "bool"])

    normalized_numerics = preprocessing.scale(numeric_df)
    normalized_df = pd.DataFrame(normalized_numerics, columns=numeric_df.columns)
    boolean_df = 2 * boolean_df.astype("float") - 1

    return pd.concat([boolean_df, normalized_df, other_df], axis=1)


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
    f"{ALTO}String",
]


Base = declarative_base()


class AnnotationLayerBatch(Base):
    __tablename__ = "layer_batches"
    id = Column(String(255), primary_key=True)
    name = Column(String(255))
    class_ = Column(String(255))

    extractor = Column(String(255), default="")
    extractor_info = Column(Text, default="")

    layers = relationship("AnnotationLayerInfo", lazy="joined", back_populates="group")

    def to_web(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "class": self.class_,
            "extractor": self.extractor,
            "extractorInfo": self.extractor_info,
            "layerCount": len(self.layers),
            "trainingLayerCount": len(list(filter(lambda l: l.training, self.layers))),
        }


class AnnotationLayerInfo(Base):
    __tablename__ = "annotationlayers"
    id = Column(String(255), primary_key=True)

    training = Column(Boolean, nullable=False)
    date = Column(DateTime, default=datetime.datetime.utcnow)

    group_id = Column(String(255), ForeignKey("layer_batches.id"))
    group = relationship("AnnotationLayerBatch", lazy="joined", back_populates="layers")

    paper_id = Column(String(255), ForeignKey("papers.id"))
    paper = relationship("Paper", lazy="joined", back_populates="layers")

    @property
    def class_(self):
        return self.group.class_

    @property
    def name(self):
        return self.group.name

    def to_web(self) -> dict:
        return {
            "id": self.id,
            "groupId": self.group_id,
            "paperId": self.paper_id,
            "name": self.name,
            "class": self.class_,
            "training": self.training,
            "created": self.date.strftime("%d/%m/%y") if self.date is not None else "UNK",
        }


class Paper(Base):
    __tablename__ = "papers"
    id = Column(String(255), primary_key=True)
    title = Column(String(255), nullable=True)
    pdf_path = Column(String(255), nullable=False, unique=True)
    metadata_directory = Column(String(255), nullable=False, unique=True)  # relative to DATA_PATH

    layers = relationship("AnnotationLayerInfo", lazy="joined", back_populates="paper")

    @property
    def meta_path(self):
        return f"{DATA_PATH}/{self.metadata_directory}"

    @property
    def n_pages(self):
        doc = fitz.open(self.pdf_path)
        return len(doc)

    def __init__(self, id: str, pdf_path: str, layers={}):
        super().__init__(id=id, pdf_path=pdf_path, metadata_directory="papers/" + id)

        if os.path.exists(self.meta_path):
            shutil.rmtree(self.meta_path)
        os.makedirs(self.meta_path)

    def has_training_layer(self, class_: str) -> bool:
        for layer in self.layers:
            if layer.class_ == class_ and layer.training:
                return True
        return False

    def get_training_layer(self, class_: str) -> Optional[AnnotationLayerInfo]:
        for layer in self.layers:
            if layer.class_ == class_ and layer.training:
                return layer
        return None

    def get_best_layer(self, class_: str) -> Optional[AnnotationLayerInfo]:
        best_layer = None
        for layer in self.layers:
            if layer.class_ == class_ and layer.training:
                return layer
            elif layer.class_ == class_:
                best_layer = layer
        return best_layer

    def get_annotation_layer(self, layer_id: str) -> AnnotationLayer:
        location = f"{self.meta_path}/annot_{layer_id}.json"
        return AnnotationLayer(location)

    def remove_annotation_layer(self, layer_id: str):
        location = f"{self.meta_path}/annot_{layer_id}.json"
        try:
            os.remove(location+".bz2")
        except Exception:
            print("exception when deleted: ", location)
            pass

        layer_index = None
        for i, layer in enumerate(self.layers):
            if layer.id == layer_id:
                layer_index = i

        if layer_index is not None:
            del self.layers[layer_index]

    def add_annotation_layer(
        self, group_id: str, content: Optional[AnnotationLayer] = None
    ) -> AnnotationLayerInfo:

        new_id = shortuuid.uuid()
        new_layer = AnnotationLayerInfo(
            id=new_id, group_id=group_id, paper_id=self.id, training=False
        )

        location = f"{self.meta_path}/annot_{new_id}.json"

        self.layers.append(new_layer)

        if content is not None:
            content.location = location
            content.save()

        return new_layer

    def get_annotation_info(self, layer_id) -> AnnotationLayerInfo:
        for layer in self.layers:
            if layer.id == layer_id:
                return layer
        raise Exception("Layer not found")

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
        else:
            subprocess.run(["bzip2", "-z", xml_path])

    def get_xml(self) -> ET.ElementTree:
        xml_path = f"{self.meta_path}/article.xml"
        if not os.path.exists(xml_path + ".bz2"):
            self.__pdfalto(xml_path)

        with bz2.BZ2File(xml_path + ".bz2", "r") as f:
            return ET.parse(f)

    def get_pdf_annotations(self) -> AnnotationLayer:
        xml_path = f"{self.meta_path}/article.xml"
        xml_annot_path = f"{self.meta_path}/article_annot.xml"
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

        req_layers_info = {x.name: self.get_best_layer(x.name) for x in only_for}
        for k, v in req_layers_info.items():
            if v is None:
                raise ParentModelNotFoundException(k)

        req_layers = {k: self.get_annotation_layer(v.id) for k, v in req_layers_info.items()}

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

    def _refresh_title(self):
        header_annot_info = self.get_best_layer("header")
        if header_annot_info is not None:
            header_annot = self.get_annotation_layer(header_annot_info.id)
            header_annot.filter(lambda x: x.label == "title")
            self.title = self.extract_raw_text(header_annot, f"{ALTO}String")
        else:
            self.title = ""

    def to_web(self, classes: List[str]) -> dict:
        class_status = {k: {"training": False, "count": 0} for k in classes}
        for layer in self.layers:
            class_ = layer.class_
            if layer.training:
                class_status[class_]["training"] = True
            class_status[class_]["count"] += 1

        if self.title == "__undef__":
            self._refresh_title()

        return {
            "id": self.id,
            "pdf": f"/papers/{self.id}/pdf",
            "classStatus": class_status,
            "title": self.title or "",
        }

    def _build_features(self, force=False) -> Dict[str, pd.DataFrame]:
        df_path = f"{self.meta_path}/features.pkl"

        if not force and os.path.exists(df_path) and not REBUILD_FEATURES:
            with open(df_path, "rb") as f:
                return pickle.load(f)
        else:
            xml = self.get_xml().getroot()
            feature_extractors = get_feature_extractors(xml)

            features_by_node = {k: [] for k in feature_extractors.keys()}
            indices = {k: 0 for k in feature_extractors.keys()}

            ancestors = []

            def dfs(node: ET.Element):
                nonlocal ancestors, indices
                if node.tag in features_by_node:
                    ancestors.append(node.tag)
                    indices[node.tag] += 1

                    features_by_node[node.tag].append(feature_extractors[node.tag].get(node))
                    if len(ancestors) > 1:
                        features_by_node[node.tag][-1][ancestors[-2]] = indices[ancestors[-2]] - 1

                for children in node:
                    dfs(children)

                if node.tag in features_by_node:
                    ancestors.pop()

            dfs(xml)

            features_dict = {k: pd.DataFrame.from_dict(v) for k, v in features_by_node.items()}

            for features in features_dict.values():
                for column in features.columns:
                    if column.startswith("#"):
                        features[column[1:]] = features[column].astype('category')
                        features.drop(column, axis=1, inplace=True)

            with open(df_path, "wb") as f:
                pickle.dump(features_dict, f)
            return features_dict

    def render(self, max_height: int = None, max_width: int = None):
        doc = fitz.open(self.pdf_path)
        pages = []
        for page in doc:
            scale = 1
            if max_height is not None:
                scale = max_height / page.bound().height
            if max_width is not None:
                scale = min(scale, max_width / page.bound().width)

            pix = page.getPixmap(matrix=fitz.Matrix(scale, scale))
            im = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            pages.append((im, scale))
        return pages

    def get_render_scales(self, max_height: int = None, max_width: int = None):
        doc = fitz.open(self.pdf_path)
        pages = []
        for page in doc:
            scale = 1
            if max_height is not None:
                scale = max_height / page.bound().height
            if max_width is not None:
                scale = min(scale, max_width / page.bound().width)
            pages.append(scale)
        return pages

    def get_features(
        self,
        leaf_node: str,
        standardize: bool = True,
        verbose: bool = False,
        add_context: bool = True,
    ) -> pd.DataFrame:
        """
        Generate features for each kind of token in PDF XML file.
        """

        # STEP 1: build features
        t0 = time.time()
        features_dict = self._build_features()
        t1 = time.time()
        if verbose:
            print("1. Build/load features: {:2f}".format(t1 - t0))

        try:
            leaf_index = ALTO_HIERARCHY.index(leaf_node)
        except ValueError:
            raise Exception("Could not find requested leaf node in the xml hierarchy.")

        # STEP 2: aggregate features
        prefix = ""
        result_df: Optional[pd.DataFrame] = None

        for index, node in reversed(list(enumerate(ALTO_HIERARCHY))):
            if node in features_dict:
                old_prefix = prefix

                if result_df is None:
                    prefix = remove_prefix(node) + "."
                    result_df = features_dict[node].add_prefix(prefix)
                else:
                    if index >= leaf_index:

                        result_df_numerics = (
                            result_df.select_dtypes(include=["bool", "number"])
                            .groupby(by=old_prefix + node)
                            .agg(["min", "max", "std", "mean"])
                            .fillna(0)
                        )
                        result_df_numerics.columns = result_df_numerics.columns.map("_".join)

                        df_non_numeric = pd.concat(
                            [
                                result_df.select_dtypes(exclude=["bool", "number"]),
                                result_df[old_prefix + node],
                            ],
                            axis=1,
                        ).groupby(by=old_prefix + node)
                        result_df_words = df_non_numeric.apply(lambda x: dict(Counter(x)))

                        df_groupby = result_df.groupby(by=old_prefix + node)

                        result_df_first_word = df_groupby.nth(0) 
                        result_df_first_word = result_df_first_word.add_suffix(".first")

                        result_df_second_word = df_groupby.nth(1) 
                        result_df_second_word = result_df_second_word.add_suffix(".second")

                        result_df_last_word = df_groupby.nth(-1) 
                        result_df_last_word = result_df_last_word.add_suffix(".last")

                        result_df = pd.concat(
                            [
                                result_df_numerics,
                                result_df_words,
                                result_df_first_word,
                                result_df_second_word,
                                result_df_last_word,
                            ],
                            axis=1,
                        )

                    prefix = remove_prefix(node) + "."
                    target = features_dict[node].add_prefix(prefix)
                    result_df = result_df.join(target, on=old_prefix + node)

                    if old_prefix + node in result_df.columns:
                        result_df = result_df.drop(old_prefix + node, axis=1)
        if result_df is None:
            raise Exception("No features generated.")

        result_df.index.name = None

        if verbose:
            t2 = time.time()
            print("2. Perform joins: {:2f}".format(t2 - t1))

        # STEP 3: add deltas:
        if add_context:
            numeric_features = result_df.select_dtypes(include="number")
            numeric_features_next = numeric_features.diff(periods=-1).add_suffix("_next").fillna(0)
            numeric_features_prev = numeric_features.diff(periods=1).add_suffix("_prev").fillna(0)
            result_df = pd.concat([result_df, numeric_features_next, numeric_features_prev], axis=1)

        if verbose:
            t3 = time.time()
            print("3. Add deltas: {:2f}".format(t3 - t2))


        # STEP 4: standardize
        if standardize:
            std = _standardize(result_df)
            if verbose:
                t4 = time.time()
                print("4. Standardize: {:2f}".format(t4 - t3))

            return std
        else:
            return result_df

    

    def get_box_validator(self, class_: AnnotationClass):

        filter_layers: List[Tuple[AnnotationLayer, List[str]]] = []
        for filter in class_.parents:
            layer_info = self.get_best_layer(filter.name)
            if layer_info is not None:
                filter_layers.append((self.get_annotation_layer(layer_info.id), filter.labels))

        def box_validator(box: BBX) -> bool:
            nonlocal filter_layers
            for layer, labels in filter_layers:
                bbx = layer.get(box)
                if bbx is not None and bbx.label in labels:
                    return True
            return False

        if len(class_.parents) > 0:
            return box_validator
        else:
            return lambda _: True


Base.metadata.create_all(SQL_ENGINE)
