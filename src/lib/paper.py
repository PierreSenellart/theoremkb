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


    def get_annotation_layer(self, layer_id: str) -> AnnotationLayer:
        location = f"{self.metadata_directory}/annot_{layer_id}.json"
        return AnnotationLayer(location)

    def remove_annotation_layer(self, layer_id: str):
        location = f"{self.metadata_directory}/annot_{layer_id}.json"
        try:
            os.remove(location)
        except Exception:
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