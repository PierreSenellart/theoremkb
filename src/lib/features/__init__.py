import lxml.etree as ET

class FeatureExtractor:
    def has(self, tag: str) -> bool:
        raise NotImplementedError

    def get(self, element: ET.Element) -> dict:
        raise NotImplementedError

    def stop_at(self, tag: str) -> bool:
        raise NotImplementedError

    def extract_features(self, accumulator, root: ET.Element, current_features: dict=None):
        if current_features is None:
            current_features = {}
 
        if self.has(root.tag):
            current_features[ET.QName(root.tag).localname] = self.get(root)
        
        if self.stop_at(root.tag):
            accumulator.append((root, dict(current_features)))
        
        for child in root:
            self.extract_features(accumulator, child, current_features)
