from __future__ import annotations
from typing import Dict, Optional, List
from enum import Enum
import os, shutil, subprocess
import jsonpickle
import shortuuid
from lxml import etree as ET
from dataclasses import dataclass

from .config import DATA_PATH
from .annotations import AnnotationLayer

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
    src_path: Optional[str]

    layers: Dict[str, AnnotationLayerInfo]

    def __init__(self, id: str, pdf_path: str, src_path: Optional[str], layers={}) -> None:
        self.id = id
        self.pdf_path = pdf_path
        self.src_path = src_path
        self.layers = layers

        self.metadata_directory = DATA_PATH + "/papers/" + id
        if os.path.exists(self.metadata_directory):
            shutil.rmtree(self.metadata_directory)
        os.makedirs(self.metadata_directory)

    def get_annotation_layer(self, layer_id: str) -> AnnotationLayer:
        location = f"{self.metadata_directory}/annot_{layer_id}.json"
        return AnnotationLayer(location)

    def remove_annotation_layer(self, layer_id: str):
        location = f"{self.metadata_directory}/annot_{layer_id}.json"
        os.remove(location)
        del self.layers[layer_id]

    def add_annotation_layer(self, meta: AnnotationLayerInfo) -> AnnotationLayer:
        location = f"{self.metadata_directory}/annot_{meta.id}.json"
        # todo: check that id is not already in use.
        self.layers[meta.id] = meta
        return AnnotationLayer(location)

    def get_annotation_meta(self, layer_id: str) -> AnnotationLayerInfo:
        return self.layers[layer_id]

    def get_xml(self) -> ET.ElementTree:
        xml_path = f"{self.metadata_directory}/article.xml"
        if not os.path.exists(xml_path):
            result = subprocess.run(["pdfalto", "-readingOrder", "-blocks", "-annotation", self.pdf_path, xml_path])
            if result.returncode != 0:
                raise Exception("Failed to convert to xml.")
        
        with open(xml_path, "r") as f:
            return ET.parse(f)
            
    def to_web(self, layers: List[str]) -> dict:
        layerStatus = {k: {"training": False, "count": 0} for k in layers}
        for layer in self.layers.values():
            if layer.training:
                layerStatus[layer.kind]["training"] = True
            layerStatus[layer.kind]["count"] += 1

        return {
            "id": self.id,
            "pdf": f"//papers/{self.id}/pdf",
            "layerStatus": layerStatus
        }