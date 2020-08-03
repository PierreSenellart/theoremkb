from lxml import etree as ET
from collections import namedtuple
from typing import List, Dict
from tqdm import tqdm
import re

from . import FeatureExtractor
from .status import StatusFeature
from ..misc.namespaces import *
from .. import misc

Font = namedtuple("Font", ["is_italic", "is_math", "is_bold", "size"])

class StringFeaturesExtractor(FeatureExtractor):
    fonts: Dict[str, Font]


    def __init__(self, root: ET.Element):
        self._extract_fonts(root)

    def _extract_fonts(self, root: ET.Element):
        italic_re   = re.compile(r"((TI)[0-9]+|Ital|rsfs|EUSM)", flags=re.IGNORECASE)
        bold_re     = re.compile(r"(CMBX|Bold|NimbusRomNo9L-Medi)", flags=re.IGNORECASE) #
        math_re     = re.compile(r"((CM)(SY|MI|EX)|math|Math|MSAM|MSBM|LASY|cmex|StandardSymL)", flags=re.IGNORECASE)
        #normal_re   = re.compile(r"(Times-Roman|CMR|CMTT|EUFM|NimbusRomNo9L-Regu|LMRoman[0-9]+-Regular)")

        self.fonts = {}

        for font in root.findall(f".//{ALTO}TextStyle"):
            family = font.get("FONTFAMILY")
            id     = font.get("ID")
            size   = float(font.get("FONTSIZE"))

            is_italic   = italic_re.search(family) is not None
            is_math     = math_re.search(family) is not None
            is_bold     = bold_re.search(family) is not None

            self.fonts[id] = Font(is_italic, is_math, is_bold, size)

    def has(self, tag: str) -> bool:
        return tag == f"{ALTO}String"
    
    def get(self, word: ET.Element) -> dict:
        if word.tag != f"{ALTO}String":
            raise KeyError

        text = word.get("CONTENT")
        font = word.get("STYLEREFS")
        line        = word.xpath(f"./ancestor::alto:TextLine", namespaces = ALTO_NS) # TextLine
        line_words  = line[0].findall(f".//{ALTO}String")
        word_index = line_words.index(word)

        word_h  = float(word.get("HPOS"))
        word_w  = float(word.get("WIDTH"))

        if word_index > 0:
            previous_word   = line_words[word_index - 1]
            previous_word_h = float(previous_word.get("HPOS")) + float(previous_word.get("WIDTH"))
        else:
            previous_word_h = word_h

        if word_index < len(line_words) - 1:
            next_word       = line_words[word_index + 1]
            next_word_h     = float(next_word.get("HPOS"))
        else:
            next_word_h     = word_h + word_w

        f = {}
        # geometry
        f["word_position"]  = str(StatusFeature.from_element(word, relative_to=f"alto:TextLine"))
        f["length"]         = len(word.get("CONTENT"))
        f["prev_delta_h"]   = word_h - previous_word_h 
        f["next_delta_h"]   = next_word_h - (word_h + word_w)
        # appearance
        f["italic"]         = self.fonts[font].is_italic
        f["math"]           = self.fonts[font].is_math
        f["bold"]           = self.fonts[font].is_bold
        f["size"]           = self.fonts[font].size
        # textual info
        f["word"]           = text
        f["word_lower"]     = text.lower()
        f["has_number"]     = re.search("[0-9]", text) is not None
        
        return f
