from __future__ import annotations
from typing import Callable, Dict, Optional
import jsonpickle, bz2
import shortuuid
import lxml.etree as ET
from typing import List, Tuple
from rtree import index
from copy import copy


from .misc.bounding_box import LabelledBBX, BBX


class AnnotationLayer:
    bbxs: Dict[str, LabelledBBX]

    _dbs: Dict[int, index.Index]  # spatial index of boxes, by page
    _id_map: Dict[int, str]  # spatial index ID to box ID
    _map_id: Dict[str, int]  # box ID to spatial index ID
    _last_c: int

    def __init__(self, location: Optional[str] = None) -> None:

        self.location = location
        if location is None:
            self.bbxs = {}
        else:
            try:
                with bz2.BZ2File(location+".bz2", "r") as f:
                    self.bbxs = jsonpickle.decode(f.read().decode())
            except Exception as e:
                print("Loading failed:", str(e))
                self.bbxs = {}

        self._dbs = {}
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

    def save(self, location: Optional[str] = None):
        if self.location is None and location is None:
            raise Exception("No location given.")

        with bz2.BZ2File((self.location or location)+".bz2", "w") as f:
            f.write(jsonpickle.encode(self.bbxs).encode())

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
        self._dbs[box.page_num].delete(self._map_id[uuid], self.bbxs[uuid].to_coor())

        self.bbxs[uuid] = box

        # update index
        self._dbs[box.page_num].add(self._map_id[uuid], box.to_coor())

    def delete_box(self, uuid: str):
        box = self.bbxs[uuid]
        box_spatial_id = self._map_id[uuid]
        # remove from index
        # print("delete: ", self._map_id[uuid], box.to_coor())
        self._dbs[box.page_num].delete(self._map_id[uuid], box.to_coor())
        del self._id_map[box_spatial_id]
        del self._map_id[uuid]
        del self.bbxs[uuid]

    def get(
        self, target_box: BBX, mode: str = "full") -> Optional[BBX]:
        if mode not in ["intersect", "full"]:
            raise Exception(f"Unknown mode {mode}")

        if target_box.page_num not in self._dbs:
            return None


        def group_size(tgt_box):
            return sum((1 for box in self.bbxs.values() if box.group == tgt_box.group and box.label == tgt_box.label))

        min_box = None
        #min_val = float('inf')

        for index_id in self._dbs[target_box.page_num].intersection(
            target_box.to_coor()
        ):
            box = self.bbxs[self._id_map[index_id]]

            if mode == "intersect":
                if box.intersects(target_box):# and group_size(box) < min_val:
                    #min_val = group_size(box)
                    min_box = box
            elif mode == "full":
                if box.extend(10).contains(target_box): #and group_size(box) < min_val:
                    #min_val = group_size(box)
                    min_box = box

        return min_box

    def get_label(self, target_box: BBX, mode: str = "full", default: str = "O") -> str:
        box = self.get(target_box, mode)
        if box is None:
            return default
        else:
            return box.label

    def filter(self, predicate: Callable[[BBX], bool]):
        to_filter = []
        for id, box in self.bbxs.items():
            if not predicate(box):
                to_filter.append(id)

        for id in to_filter:
            self.delete_box(id)

    def filter_map(self, f_mapper: Callable[[str, int], [str, int]]):
        to_filter = []
        for id, box in self.bbxs.items():
            new_info = f_mapper(box.label, box.group)
            if new_info is None:
                to_filter.append(id)
            else:
                box.label, box.group = new_info

        for id in to_filter:
            self.delete_box(id)

    def reduce(self) -> AnnotationLayer:
        """
        Reduce the number of bounding boxes by merging boxes of
        same category. 
        """
        print("number of boxes:", len(self.bbxs))
        # build a new layer
        new_layer = AnnotationLayer()

        # store a mapping box group -> List of boxes composing that group
        by_group: Dict[Tuple[str, int], List[int]] = {}

        for box_id, box in self.bbxs.items():
            group_key = (box.label, box.group)
            if group_key not in by_group:
                by_group[group_key] = []

            by_group[group_key].append(self._map_id[box_id])

        # for each group, merge boxes.
        for ids in by_group.values():

            current_box = copy(self.bbxs[self._id_map[ids[0]]])

            for id in ids[1:]:
                # let's try to merge these two boxes.
                test_box    = self.bbxs[self._id_map[id]]

                if current_box.page_num != test_box.page_num: # flush box as page changed.
                    new_layer.add_box(current_box)
                    current_box = copy(test_box)
                    continue

                # test merging the two boxes, checking if that doesn't intersect with another group. 
                result_box, extensions_box = current_box.group_with(test_box, inplace=False, extension=True)

                intersection = set()

                for extension_box in extensions_box:
                    intersection = intersection.union(self._dbs[result_box.page_num].intersection(extension_box.to_coor()))

                if intersection.issubset(ids): # it doesn't intersect with another group. we can merge the boxes.
                    current_box = result_box
                else: # it does intersect: we flush current box.
                    new_layer.add_box(current_box)
                    current_box = copy(test_box)
            # flush last box
            new_layer.add_box(current_box)
        print("number of boxes in new layer:", len(new_layer.bbxs))
        return new_layer



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
