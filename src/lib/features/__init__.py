"""Feature extraction"""

from abc import abstractmethod
import lxml.etree as ET

class FeatureExtractor:
    """Hierarchical feature extractor
    
    Feature extractors operate on a set of nodes and can be composed to extract multi-scale features on a document.
    """

    @abstractmethod
    def has(self, tag: str) -> bool:
        """Check if node tag is handled by the extractor."""

    @abstractmethod
    def get(self, element: ET.Element) -> dict:
        """Get features for given node."""

    @abstractmethod
    def stop_at(self, tag: str) -> bool:
        """Check if token should be stored along with extracted features."""

    def extract_features(self, accumulator, root: ET.Element, current_features: dict=None):
        """Parse the document and extract features given the extractor rules.
        """
        if current_features is None:
            current_features = {}
 
        if self.has(root.tag):
            current_features[ET.QName(root.tag).localname] = self.get(root)
        
        if self.stop_at(root.tag):
            accumulator.append((root, dict(current_features)))
        
        for child in root:
            self.extract_features(accumulator, child, current_features)
