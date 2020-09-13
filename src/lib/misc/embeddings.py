from typing import List

from ..paper import Paper
from .bounding_box import BBX
from .namespaces import ALTO
from . import get_pattern

def build_vocabulary(size: int, documents: List[Paper]) -> dict:
    # count items and select most common.
    vocab = {}
    for paper, _ in documents:
        for token in paper.get_xml().getroot().findall(f".//{ALTO}String"):
            bbx = BBX.from_element(token)
            text = get_pattern(token.get("CONTENT"))
            vocab[text] = vocab.get(text, 0) + 1

    sorted_vocab = sorted(vocab.items(), key=lambda x: x[1], reverse=True)
    sorted_vocab = list(map(lambda x: x[0], sorted_vocab))[:size-2]
    return {x: y + 2 for y, x in enumerate(sorted_vocab)}
