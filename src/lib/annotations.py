from __future__ import annotations
from typing import Callable, Dict, Optional
from enum import Enum
import os
import shutil
import subprocess
import jsonpickle
import shortuuid
import lxml.etree as ET
from typing import List, Tuple
from rtree import index
import re


from .config import DATA_PATH
from .misc.bounding_box import LabelledBBX, BBX


class AnnotationLayer:
    bbxs: Dict[str, LabelledBBX]

    _dbs: Dict[int, index.Index]  # spatial index of boxes, by page
    _id_map: Dict[int, str]      # spatial index ID to box ID
    _map_id: Dict[str, int]      # box ID to spatial index ID
    _last_c: int

    def __init__(self, location: Optional[str] = None) -> None:
        
        self.location = location
        if location is None:
            self.bbxs = {}
        else:
            try:
                with open(location, "r") as f:
                    self.bbxs = jsonpickle.decode(f.read()).bbxs
            except Exception as e:
                print("Loading failed:", str(e))
                self.bbxs = {}

        self._dbs    = {}
        self._id_map = {}
        self._map_id = {}
        self._last_c = 0

        # construct spatial index
        for id, box in self.bbxs.items():
            if box.page_num not in self._dbs:
                self._dbs[box.page_num] = index.Index()
            self._dbs[box.page_num].insert(self._last_c, box.to_coor())
            self._id_map[self._last_c] = id
            self._map_id[id] = self._last_c
            self._last_c += 1
            

    def __str__(self) -> str:
        return "\n".join([k + ":" + str(x) for k, x in self.bbxs.items()])

    def get_boxes(self) -> Dict[str, LabelledBBX]:
        return self.bbxs

    def add_box(self, box: LabelledBBX) -> str:
        uuid = shortuuid.uuid()
        self.bbxs[uuid] = box

        # update index
        if box.page_num not in self._dbs:
            self._dbs[box.page_num] = index.Index()
        self._dbs[box.page_num].insert(self._last_c, box.to_coor())
        self._id_map[self._last_c] = uuid
        self._map_id[uuid] = self._last_c
        self._last_c += 1

        return uuid

    def move_box(self, uuid: str, box: LabelledBBX):
        # remove from index
        self._dbs[box.page_num].delete(
            self._map_id[uuid], self.bbxs[uuid].to_coor())

        self.bbxs[uuid] = box

        # update index
        self._dbs[box.page_num].add(self._map_id[uuid], box.to_coor())

    def delete_box(self, uuid: str):
        box = self.bbxs[uuid]
        box_spatial_id = self._map_id[uuid]
        # remove from index
        self._dbs[box.page_num].delete(self._map_id[uuid], box.to_coor())
        del self._id_map[box_spatial_id]
        del self._map_id[uuid]
        del self.bbxs[uuid]

    def save(self, location: Optional[str] = None):
        if self.location is None and location is None:
            raise Exception("No location given.")

        with open(self.location or location or "", "w") as f:
            f.write(jsonpickle.encode(self))

    
    def get(self, target_box: BBX, mode: str = "full", default: str = "O") -> Tuple[str, int]:
        if mode not in ["intersect", "full"]:
            raise Exception(f"Unknown mode {mode}")

        if target_box.page_num not in self._dbs:
            return default, -1

        for index_id in self._dbs[target_box.page_num].intersection(target_box.to_coor()):
            box = self.bbxs[self._id_map[index_id]]

            if mode == "intersect":
                if box.intersects(target_box):
                    return box.label, box.number
            elif mode == "full":
                if box.extend(10).contains(target_box):
                    return box.label, box.number

        return default, -1


    def get_label(self, target_box: BBX, mode: str = "full", default: str = "O") -> str:
        return self.get(target_box, mode, default)[0]

    def filter(self, predicate: Callable[[str], bool]):
        to_filter = []
        for id, box in self.bbxs.items():
            if not predicate(box.label):
                to_filter.append(id)
        
        for id in to_filter:
            self.delete_box(id)
        
    def filter_map(self, f_mapper: Callable[[str, int], [str, int]]):
        to_filter = []
        for id, box in self.bbxs.items():
            new_info = f_mapper(box.label, box.number)
            if new_info is None:
                to_filter.append(id)
            else:
                box.label, box.number = new_info
                
        for id in to_filter:
            self.delete_box(id)

    def reduce(self, reference_layer: AnnotationLayer = None):
        if reference_layer is None:
            reference_layer = self

        by_group: Dict[Tuple[str, int], List[int]] = {}

        for id, box in self.bbxs.items():
            group_key = (box.label, box.number)
            if group_key not in by_group:
                by_group[group_key] = []

            by_group[group_key].append(self._map_id[id])

        print("length before: ", len(self.bbxs))
        print("n groups: ", len(by_group))

        for ids in by_group.values():
            current_id = ids[0]
            for id in ids[1:]:
                current_box = self.bbxs[self._id_map[current_id]]
                # let's try to merge these two boxes.
                test_box = self.bbxs[self._id_map[id]]

                if current_box.page_num != test_box.page_num:
                    current_id = id
                    continue

                result_box = current_box.group_with(test_box, inplace=False)

                intersection = set(self._dbs[result_box.page_num].intersection(result_box.to_coor()))

                if intersection.issubset(ids):
                    self.move_box(self._id_map[current_id], result_box)
                    self.delete_box(self._id_map[id])
                else:
                    current_id = id
        
        print("length after: ", len(self.bbxs))

    @staticmethod
    def from_pdf_annotations(pdf_annot: ET.ElementTree) -> AnnotationLayer:
        layer = AnnotationLayer()

        for annotation in pdf_annot.findall(".//ANNOTATION/ACTION[@type='uri']/.."):
            dest = annotation.find("ACTION/DEST").text

            page_num = int(annotation.get("pagenum"))

            quadpoints = annotation.findall("QUADPOINTS/QUADRILATERAL/POINT")
            min_h, min_v, max_h, max_v = None, None, None, None
            for point in quadpoints:
                h, v = float(point.get("HPOS")), float(point.get("VPOS"))

                if min_h is None:
                    min_h, max_h = h, h
                    min_v, max_v = v, v
                else:
                    min_h = min(min_h, h)
                    max_h = max(max_h, h)
                    min_v = min(min_v, v)
                    max_v = max(max_v, v)
            box = BBX(page_num, min_h, min_v, max_h, max_v)
            layer.add_box(LabelledBBX.from_bbx(box, dest, 0))

        return layer
