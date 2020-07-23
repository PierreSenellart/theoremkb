from .. import Layer 


results_schema = {
    "type": "object",
    "properties": {
        "label": {
            "type": "string",
            "enum": ["theorem", "lemma", "proof", "definition", None]
        }
        
    },
    "required": "label"
}

class ResultsLayer(Layer):
    def __init__(self):
        super().__init__("results", results_schema)
