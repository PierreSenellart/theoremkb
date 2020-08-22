from __future__ import annotations

from enum import Enum
from lxml import etree as ET

from ..misc.namespaces import *

def get_status(element: ET.Element, relative_to: str) -> str:
    parent = element.xpath(f"./ancestor::{relative_to}", namespaces=ALTO_NS)
    assert len(parent) == 1
    children = parent[0].findall(f".//{element.tag}")
    position = children.index(element)

    if position == 0:
        return "start"
    elif position == len(children) - 1:
        return "end"
    else:
        return "in"
