from .. import Layer 

fulltext_schema = {
    "type": "object",
    "properties": {
        "label": {
            "type": "string",
            "enum": ["paragraph", "heading", "figure", "table", None]
        }
        
    },
    "required": "label"
}

class FullTextLayer(Layer):
    def __init__(self):
        super().__init__("fulltext", fulltext_schema)
