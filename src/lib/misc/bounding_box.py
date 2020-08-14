from __future__ import annotations
from copy import copy, deepcopy
from typing import List
from lxml import etree as ET

from ..misc.namespaces import *

# from ..tkb import TheoremKB


class BBX:
    """
    Bounding box in a PDF.
    """

    page_num: int
    min_h: float
    min_v: float
    max_h: float
    max_v: float

    def __init__(self, page_num: int, min_h: float, min_v: float, max_h: float, max_v: float):
        self.page_num = page_num
        self.min_h = min_h
        self.min_v = min_v
        self.max_h = max(min_h, max_h)
        self.max_v = max(min_v, max_v)

    def contains(self, other):
        """
        Check if this bounding box contains the other.
        """
        return (
            self.page_num == other.page_num
            and other.min_h >= self.min_h
            and other.min_v >= self.min_v
            and other.max_h <= self.max_h
            and other.max_v <= self.max_v
        )

    def intersects(self, other: BBX):
        """
        Check if this bounding box intersects the other. 
        """
        return (
            self.page_num == other.page_num
            and other.max_h >= self.min_h
            and self.max_h >= other.min_h
            and other.max_v >= self.min_v
            and self.max_v >= other.min_v
        )

    def group_with(self, other: BBX, inplace: bool = True) -> BBX:
        """
        Inplace merge two bounding boxes from the same page.
        """
        assert self.page_num == other.page_num
        if not inplace:
            self = copy(self)
        self.min_h = min(self.min_h, other.min_h)
        self.max_h = max(self.max_h, other.max_h)
        self.min_v = min(self.min_v, other.min_v)
        self.max_v = max(self.max_v, other.max_v)
        return self

    def extend(self, d):
        copied = copy(self)
        copied.min_h -= d
        copied.max_h += d
        copied.min_v -= d
        copied.max_v += d
        return copied

    def to_coor(self) -> List[float]:
        return [self.min_h, self.min_v, self.max_h, self.max_v]

    @staticmethod
    def from_list(lst):
        by_page = {}

        for b in lst:
            if b.page_num not in by_page:
                by_page[b.page_num] = b
            else:
                by_page[b.page_num].group_with(b)

        return by_page.values()

    @staticmethod
    def from_element(node: ET.Element):
        min_h, min_v = float(node.get("HPOS")), float(node.get("VPOS"))
        max_h, max_v = (
            min_h + float(node.get("WIDTH", default=0)),
            min_v + float(node.get("HEIGHT", default=0)),
        )

        while node.tag != f"{ALTO}Page":
            node = node.getparent()
        page_num = int(node.get("PHYSICAL_IMG_NR"))
        return BBX(page_num, min_h, min_v, max_h, max_v)


class LabelledBBX(BBX):
    label: str
    group: int

    def __init__(self, label: str, group: int, page_num, min_h, min_v, max_h, max_v):
        self.label = label
        self.group = group
        self.page_num = page_num
        self.min_h = min_h
        self.min_v = min_v
        self.max_h = max_h
        self.max_v = max_v

    def __str__(self) -> str:
        return f"{self.label}-{self.group}:{self.min_h}|{self.min_v}|{self.max_h}|{self.max_v}@{self.page_num}"

    @staticmethod
    def from_bbx(bbx, label, group) -> LabelledBBX:
        return LabelledBBX(label, group, bbx.page_num, bbx.min_h, bbx.min_v, bbx.max_h, bbx.max_v)

    def to_web(self, id: str, paperId: str, layerId: str) -> dict:
        return {
            "id": id,
            "paperId": paperId,
            "layerId": layerId,
            "pageNum": self.page_num,
            "minH": self.min_h,
            "minV": self.min_v,
            "maxH": self.max_h,
            "maxV": self.max_v,
            "label": self.label,
            "group": self.group,
        }
