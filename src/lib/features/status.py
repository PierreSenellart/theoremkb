from __future__ import annotations

from enum import Enum
from lxml import etree as ET

from ..misc.namespaces import *

class StatusFeature(Enum):
    START = "start"
    IN    = "in"
    END   = "end"

    @staticmethod
    def from_element(element: ET.Element, relative_to: str) -> StatusFeature:
        parent   = element.xpath(f"./ancestor::{relative_to}", namespaces=ALTO_NS)
        assert len(parent) == 1
        children = parent[0].findall(f".//{element.tag}")
        position = children.index(element)

        if position == 0:
            return StatusFeature.START
        elif position == len(parent) - 1:
            return StatusFeature.END
        else:
            return StatusFeature.IN
