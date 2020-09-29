from lxml import etree as ET

from . import FeatureExtractor
from .status import get_status
from ..misc.namespaces import *
from .. import misc


class TextBlockFeaturesExtractor(FeatureExtractor):
    def __init__(self, root: ET.Element):
        pass

    def has(self, tag: str) -> bool:
        return tag == f"{ALTO}TextBlock"

    def get(self, block: ET.Element) -> dict:
        if block.tag != f"{ALTO}TextBlock":
            raise KeyError

        page = block.xpath(f"./ancestor::alto:Page", namespaces=ALTO_NS)[0]
        page_blocks = page.findall(f".//{ALTO}TextBlock")

        block_index = page_blocks.index(block)

        block_h = float(block.get("HPOS"))
        block_v = float(block.get("VPOS"))
        block_w = float(block.get("WIDTH"))
        block_height = float(block.get("HEIGHT"))

        page_height = float(page.get("HEIGHT"))
        page_w = float(page.get("WIDTH"))

        if block_index > 0:
            previous_block = page_blocks[block_index - 1]
            previous_block_v = float(previous_block.get("VPOS")) + float(
                previous_block.get("HEIGHT")
            )
        else:
            previous_block_v = 0

        if block_index < len(page_blocks) - 1:
            next_block = page_blocks[block_index + 1]
            next_block_v = float(next_block.get("VPOS"))
        else:
            next_block_v = page_height

        f = {}
        # geometry
        f["#block_position"] = get_status(block, relative_to="alto:Page")

        f["prev_delta_h"] = block_h
        f["next_delta_h"] = page_w - (block_h + block_w)
        f["prev_delta_v"] = block_v - previous_block_v
        f["next_delta_v"] = next_block_v - (block_v + block_height)

        return f
