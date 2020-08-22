from lxml import etree as ET
import re
from .namespaces import *


def get_text(node: ET.Element) -> str:

    result = ""

    if node.tag == f"{ALTO}String":
        result = node.get("CONTENT")
    elif node.tag == f"{ALTO}SP":
        result = " "

    for children in node:
        result += get_text(children)

    if node.tag == f"{ALTO}TextLine":
        result += "\n"

    return result


REG_NOT_LETTERS = re.compile("[^a-zA-Z ]")
REG_NUMBERS = re.compile("[0-9]")


def get_pattern(text):
    text = REG_NOT_LETTERS.sub("", text)
    text = REG_NUMBERS.sub("X", text)
    return text.lower()

def remove_prefix(k: str):
    if "}" in k: 
        return k.split("}")[1]
    else:
        return k