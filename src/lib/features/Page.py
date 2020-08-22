from lxml import etree as ET
from collections import namedtuple
from typing import List, Dict
from tqdm import tqdm
import re

from . import FeatureExtractor
from .status import get_status
from ..misc.namespaces import *
from .. import misc


class PageFeaturesExtractor(FeatureExtractor):
    def __init__(self, root: ET.Element):
        pass

    def has(self, tag: str) -> bool:
        return tag == f"{ALTO}Page"

    def get(self, page: ET.Element) -> dict:
        if page.tag != f"{ALTO}Page":
            raise KeyError

        f = {}
        # geometry
        f["page_position"] = get_status(page, relative_to="alto:Layout")

        return f
