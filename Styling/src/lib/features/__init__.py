"""## Feature extraction

Features are hierarchical numerical/text descriptors for PDF articles. 
They are extracted automatically when using `lib.paper.Paper.get_features` and can be used for machine learning purposes.
"""

import lxml.etree as ET
from abc import abstractmethod
from typing import Dict

from ..misc.namespaces import *


class FeatureExtractor:
    """Extracts features for a kind of node."""

    @abstractmethod
    def has(self, tag: str) -> bool:
        """Check if node tag is handled by the extractor."""

    @abstractmethod
    def get(self, element: ET.Element) -> dict:
        """Get features for given node."""


from .String import StringFeaturesExtractor
from .Page import PageFeaturesExtractor
from .TextBlock import TextBlockFeaturesExtractor
from .TextLine import TextLineFeaturesExtractor


def get_feature_extractors(root: ET.Element) -> Dict[str, FeatureExtractor]:
    """Get feature extractor for each kind of node."""
    return {
        f"{ALTO}Page": PageFeaturesExtractor(root),
        f"{ALTO}TextBlock": TextBlockFeaturesExtractor(root),
        f"{ALTO}TextLine": TextLineFeaturesExtractor(root),
        f"{ALTO}String": StringFeaturesExtractor(root),
    }
