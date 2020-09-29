from __future__ import annotations

import os, bz2, shutil, subprocess, pickle, json, time, datetime
import fitz, shortuuid, pandas as pd, numpy as np
from typing import Dict, Optional, List, Tuple
from lxml import etree as ET
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy import String, Column, ForeignKey, DateTime, Text, Table

from ..classes import AnnotationClass, AnnotationClassFilter
from ..config import config
from ..annotations import AnnotationLayer
from ..misc.bounding_box import BBX, LabelledBBX
from ..misc.namespaces import *
from . import features


class ParentModelNotFoundException(Exception):
    kind: str


Base = declarative_base()

association_table = Table(
    "layer_tags",
    Base.metadata,
    Column("tag_id", String(255), ForeignKey("tags.id")),
    Column("layer_id", String(255), ForeignKey("annotationlayers.id")),
)


class AnnotationLayerInfo(Base):
    __tablename__ = "annotationlayers"
    id = Column(String(255), primary_key=True)

    class_ = Column(String(255))
    date = Column(DateTime, default=datetime.datetime.utcnow)

    tags = relationship(
        "AnnotationLayerTag",
        secondary=association_table,
        lazy="joined",
        back_populates="layers",
    )

    paper_id = Column(String(255), ForeignKey("papers.id"), nullable=False)
    paper = relationship("Paper", lazy="joined", back_populates="layers")

    @property
    def training(self):
        return any([t.data.get("training", False) for t in self.tags])

    def to_web(self) -> dict:
        return {
            "id": self.id,
            "paperId": self.paper_id,
            "class": self.class_,
            "created": self.date.strftime("%d/%m/%y")
            if self.date is not None
            else "UNK",
        }


class AnnotationLayerTag(Base):
    __tablename__ = "tags"
    id = Column(String(255), primary_key=True)
    name = Column(String(255))
    readonly = Column(Boolean)

    data_str = Column(Text, default="{}")

    layers = relationship(
        "AnnotationLayerInfo", secondary=association_table, back_populates="tags"
    )

    @property
    def data(self):
        return json.loads(self.data_str)

    @data.setter
    def data(self, data: dict):
        self.data_str = json.dumps(data)

    def to_web(self, counts: Optional[dict] = None) -> dict:
        res = {
            "id": self.id,
            "name": self.name,
            "readonly": self.readonly,
            "data": self.data,
        }

        if counts is not None:
            res["counts"] = counts
        return res


class Paper(Base):
    __tablename__ = "papers"
    id = Column(String(255), primary_key=True)
    title = Column(String(255), nullable=True)
    pdf_path = Column(String(255), nullable=False)
    metadata_directory = Column(
        String(255), nullable=False, unique=True
    )  # relative to DATA_PATH

    layers = relationship(
        "AnnotationLayerInfo",
        lazy="joined",
        back_populates="paper",
        cascade="save-update,delete",
    )

    @property
    def meta_path(self):
        return f"{config.DATA_PATH}/{self.metadata_directory}"

    @property
    def n_pages(self):
        doc = fitz.open(self.pdf_path)
        return len(doc)

    def __init__(self, id: str, pdf_path: str, layers={}):
        super().__init__(id=id, pdf_path=pdf_path, metadata_directory="papers/" + id)

        if os.path.exists(self.meta_path):
            shutil.rmtree(self.meta_path)
        os.makedirs(self.meta_path)

    def get_best_layer(self, class_: str) -> Optional[AnnotationLayerInfo]:
        best_layer = None

        for layer in self.layers:
            if layer.class_ == class_:
                if best_layer is None or layer.date > best_layer.date:
                    best_layer = layer

        return best_layer

    def get_annotation_layer(self, layer_id: str) -> AnnotationLayer:
        location = f"{self.meta_path}/annot_{layer_id}.json"
        return AnnotationLayer(location)

    def remove_annotation_layer(self, session, layer_id: str):
        location = f"{self.meta_path}/annot_{layer_id}.json"
        try:
            os.remove(location + ".bz2")
        except Exception:
            print("exception when deleted: ", location)

        session.delete(self.get_annotation_info(layer_id))

    def add_annotation_layer(
        self, class_: str, content: Optional[AnnotationLayer] = None
    ) -> AnnotationLayerInfo:

        new_id = shortuuid.uuid()
        new_layer = AnnotationLayerInfo(
            id=new_id,
            class_=class_,
            paper_id=self.id,
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

        req_layers = {
            k: self.get_annotation_layer(v.id) for k, v in req_layers_info.items()
        }

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
                    layer.add_box(
                        LabelledBBX.from_bbx(bbx, box.label, box.group, box.user_data)
                    )

        return layer

    def extract_raw_text(self, annotations: AnnotationLayer, target: str) -> str:
        result = []

        for child in self.get_xml().findall(f".//{target}"):
            bbx = BBX.from_element(child)
            if annotations.get_label(bbx, mode="full") != "O":
                result.append(child.get("CONTENT"))

            if bbx.page_num > max(annotations._dbs.keys(), default=0):
                break

        return " ".join(result)

    def _refresh_title(self):
        header_annot_info = self.get_best_layer("header")
        if header_annot_info is not None:
            t0 = time.time()
            header_annot = self.get_annotation_layer(header_annot_info.id)
            header_annot.filter(lambda x: x.label == "title")
            self.title = self.extract_raw_text(header_annot, f"{ALTO}String")
        else:
            self.title = ""

    def to_web(self, classes: List[str]) -> dict:
        class_status = {k: {"count": 0} for k in classes}
        for layer in self.layers:
            class_ = layer.class_
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

        if not force and os.path.exists(df_path) and not config.REBUILD_FEATURES:
            with open(df_path, "rb") as f:
                return pickle.load(f)
        else:
            features_dict = features.build_features_dict(self.get_xml().getroot())
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
        add_context: bool = True,
    ) -> pd.DataFrame:
        return features.get_features(
            self._build_features(), leaf_node, standardize, add_context
        )

    def get_box_validator(self, class_: AnnotationClass):

        filter_layers: List[Tuple[AnnotationLayer, List[str]]] = []
        for filter in class_.parents:
            layer_info = self.get_best_layer(filter.name)
            if layer_info is not None:
                filter_layers.append(
                    (self.get_annotation_layer(layer_info.id), filter.labels)
                )

        def box_validator(box: BBX) -> bool:
            for layer, labels in filter_layers:
                print(layer.bbxs)
                bbx = layer.get(box)
                print(">", bbx, "(", box, ")")
                if bbx is not None and bbx.label in labels:
                    return True
            return False

        if len(class_.parents) > 0:
            return box_validator
        else:
            return lambda _: True
