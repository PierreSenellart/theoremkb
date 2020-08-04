from __future__ import annotations
from typing import Dict, Optional, List, Tuple
from enum import Enum
import os, shutil, subprocess
import jsonpickle
import shortuuid
from lxml import etree as ET
from dataclasses import dataclass
import time

from .config import DATA_PATH
from .annotations import AnnotationLayer
from .misc.bounding_box import BBX, LabelledBBX
from.misc.namespaces import *

@dataclass
class AnnotationLayerInfo:
    """ Annotation layer metadata """
    id: str
    name: str
    kind: str
    training: bool

    def to_web(self, paper_id: str) -> dict:
        return {**self.__dict__, "paperId": paper_id}


class Paper():

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

    def has_training_layer(self, kind: str) -> bool:
        for layer in self.layers.values():
            if layer.kind == kind and layer.training:
                return True
        return False
    
    def get_training_layer(self, kind: str) -> Optional[AnnotationLayerInfo]:
        for layer in self.layers.values():
            if layer.kind == kind and layer.training:
                return layer
        return None

    def get_best_layer(self, kind: str) -> Optional[AnnotationLayerInfo]:
        a_layer = None
        for layer in self.layers.values():
            if layer.kind == kind and layer.training:
                return layer
            elif layer.kind == kind:
                a_layer = layer
        return a_layer

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

    def add_annotation_layer(self, meta: AnnotationLayerInfo, content: Optional[AnnotationLayer] = None) -> AnnotationLayer:
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
        result = subprocess.run(["pdfalto", "-readingOrder", "-blocks", "-annotation", self.pdf_path, xml_path])
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

    def apply_annotations_on(self, annotations: AnnotationLayer, target: str, only_for: List[Tuple[str, List[str]]]=[]) -> AnnotationLayer:
        layer = AnnotationLayer()

        req_layers = {x[0]: self.get_best_layer(x[0]) for x in only_for}
        if None in req_layers.values():
            raise Exception("no model found for parent ("+str(only_for)+")")
        req_layers = {k: self.get_annotation_layer(v.id) for k,v in req_layers.items()}

        for child in self.get_xml().findall(f".//{target}"):
            bbx = BBX.from_element(child)

            ok = False
            if only_for == []:
                ok = True
            else:
                for kind, allowed_tags in only_for:
                    if req_layers[kind].get_label(bbx) in allowed_tags:
                        ok = True
                        break
            
            if ok:
                label, group = annotations.get(bbx, mode="full")
                layer.add_box(LabelledBBX.from_bbx(bbx, label, group))

        return layer


    def extract_raw_text(self, annotations: AnnotationLayer, target: str) -> str:
        result = []

        for child in self.get_xml().findall(f".//{target}"):
            bbx = BBX.from_element(child)
            if annotations.get_label(bbx, mode="full") != "O":
                result.append(child.get("CONTENT"))
                
        return " ".join(result)
    
    def to_web(self, layers: List[str]) -> dict:
        layerStatus = {k: {"training": False, "count": 0} for k in layers}
        for layer in self.layers.values():
            if layer.training:
                layerStatus[layer.kind]["training"] = True
            layerStatus[layer.kind]["count"] += 1

        header_annot_info = self.get_best_layer("header")
        title = ""
    
        if header_annot_info is not None:
            header_annot = self.get_annotation_layer(header_annot_info.id)
            header_annot.filter(lambda x: x == "title")
            title = self.extract_raw_text(header_annot, f"{ALTO}String")

        return {
            "id": self.id,
            "pdf": f"//papers/{self.id}/pdf",
            "layerStatus": layerStatus,
            "title": title
        }