from lxml import etree as ET
from collections import namedtuple
from typing import List, Dict
from tqdm import tqdm
import re

from . import FeatureExtractor
from .status import StatusFeature
from ..misc.namespaces import *
from .. import misc


class TextLineFeaturesExtractor(FeatureExtractor):
    patterns: Dict[str, int]
    patterns_first: Dict[str, ET.Element]

    def __init__(self, root: ET.Element):
        self.patterns = {}
        self.patterns_first = {}

        # Identify block patterns.
        # this is a block feature extractor..
        for page in root.findall(f".//{ALTO}Page"):
            blocks = page.findall(f".//{ALTO}TextBlock")
            for block in [blocks[0], blocks[1], blocks[-1]]:
                text = misc.get_text(block)
                first_line = text.split("\n")[0]
                pattern = misc.get_pattern(first_line)

                if len(pattern) <= 8:
                    continue

                if pattern in self.patterns:
                    self.patterns[pattern] += 1
                else:
                    self.patterns[pattern] = 1
                    self.patterns_first[pattern] = block

    def has(self, tag: str) -> bool:
        return tag == f"{ALTO}TextLine"

    def get(self, line: ET.Element) -> dict:
        if line.tag != f"{ALTO}TextLine":
            raise KeyError

        block = line.xpath(f"./ancestor::alto:TextBlock", namespaces=ALTO_NS)[
            0
        ]  # TextBlock
        block_lines = block.findall(f".//{ALTO}TextLine")
        line_index = block_lines.index(line)

        line_text = misc.get_text(line)

        line_h = float(line.get("HPOS"))
        line_v = float(line.get("VPOS"))
        line_w = float(line.get("WIDTH"))
        line_height = float(line.get("HEIGHT"))

        block_h = float(block.get("HPOS"))
        block_w = float(block.get("WIDTH"))

        if line_index > 0:
            previous_line = block_lines[line_index - 1]
            previous_line_v = float(previous_line.get("VPOS")) + float(
                previous_line.get("HEIGHT")
            )
        else:
            previous_line_v = line_v

        if line_index < len(block_lines) - 1:
            next_line = block_lines[line_index + 1]
            next_line_v = float(next_line.get("VPOS"))
        else:
            next_line_v = line_v + line_height

        f = {}
        # geometry
        f["line_position"] = str(
            StatusFeature.from_element(line, relative_to=f"alto:TextBlock")
        )
        # f["position_h"]     = line_h
        # f["position_v"]     = line_v
        f["prev_delta_h"] = line_h - block_h
        f["next_delta_h"] = block_h + block_w - (line_h + line_w)
        f["prev_delta_v"] = line_h - previous_line_v
        f["next_delta_v"] = next_line_v - (line_v + line_height)

        f["repetitive"] = False
        f["repetitive_first"] = False
        if line_index < 2 or line_index >= len(block_lines) - 1:
            f["repetitive"] = line_text in self.patterns
            if line_text in self.patterns:
                f["repetitive_first"] = self.patterns_first[line_text] == block

        return f
