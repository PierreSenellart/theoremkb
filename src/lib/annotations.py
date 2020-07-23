from __future__ import annotations
from typing import Dict, Optional
from enum import Enum
import os, shutil, subprocess
import jsonpickle
import shortuuid
import lxml.etree as ET
from typing import List, Tuple
from rtree import index


from .config import DATA_PATH
from .misc.bounding_box import LabelledBBX, BBX


class AnnotationLayer:
    bbxs: Dict[str, LabelledBBX]

    def __init__(self, location: Optional[str]=None) -> None:
        self.location = location
        if location is None:
            self.bbxs = {}
            return
        
        try:
            with open(location, "r") as f:
                self.bbxs = jsonpickle.decode(f.read()).bbxs
        except Exception as e:
            print("Loading failed:", str(e))
            self.bbxs     = {}

    def __str__(self) -> str:
        return "\n".join([k + ":" + str(x) for k, x in self.bbxs.items()])
        
    
    def get_boxes(self) -> Dict[str, LabelledBBX]:
        return self.bbxs

    def add_box(self, box: LabelledBBX) -> str:
        uuid = shortuuid.uuid()
        self.bbxs[uuid] = box
        return uuid

    def move_box(self, uuid: str, target: LabelledBBX):
        self.bbxs[uuid] = target

    def delete_box(self, uuid: str):
        del self.bbxs[uuid]

    def save(self, location: Optional[str]=None):
        if self.location is None and location is None:
            raise Exception("No location given.")

        with open(self.location or location or "", "w") as f:
            f.write(jsonpickle.encode(self))


    def get_label(self, target_box: BBX, mode: str = "intersect", default: str = "O") -> str:
        for id, box in self.bbxs.items():
            if mode == "intersect":
                if box.intersects(target_box):
                    return box.label
            elif mode == "full":
                if box.extend(10).contains(target_box):
                    return box.label
            else:
                raise Exception(f"Unknown mode {mode}")
        return default

    def reduce(self):
        dbs: Dict[int, index.Index] = {}

        by_group: Dict[Tuple[str, int], list] = {}
        id_map: Dict[int, str] = {}
        
        for c, (id, box) in enumerate(self.bbxs.items()):
            if box.page_num not in dbs:
                dbs[box.page_num] = index.Index()
            dbs[box.page_num].insert(c, box.to_coor())

            group_key = (box.label, box.number)
            if group_key not in by_group:
                by_group[group_key] = []
            by_group[group_key].append(c)
            id_map[c] = id

        print("length before: ", len(self.bbxs))
        print(dbs.keys())
        
        for ids in by_group.values():
            current_id = ids[0]
            for id in ids[1:]:
                current_box = self.bbxs[id_map[current_id]] #
                test_box    = self.bbxs[id_map[id]]            # let's try to merge these two boxes.

                if current_box.page_num != test_box.page_num:
                    current_id = id
                    continue

                result_box  = current_box.group_with(test_box, inplace=False) 
                 
                intersection = set(dbs[result_box.page_num].intersection(result_box.to_coor()))

                if intersection.issubset(ids):
                    current_box.group_with(test_box) # perform merge
                    del self.bbxs[id_map[id]]
                else:
                    current_id = id
        
        print("length after: ", len(self.bbxs))

            
