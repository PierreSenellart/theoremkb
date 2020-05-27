from collections import namedtuple
from lxml import etree as ET
import sys,os,re,pickle
from copy import copy
from tqdm import tqdm
from joblib import Parallel, delayed  
import pandas as pd

from ..config import TARGET_PATH, FEATURE_MODE, DATA_PATH
from ..theoremdb.db import TheoremDB, Paper
from ..theoremdb.results import ResultsBoundingBoxes

ALTO = "{http://www.loc.gov/standards/alto/ns-v3#}"


def extract_fonts(xml):
    Font = namedtuple("Font", ["is_italic", "is_math", "is_bold", "size"])

    italic_re   = re.compile(r"((TI)[0-9]+|Ital|rsfs|EUSM)", flags=re.IGNORECASE)
    bold_re     = re.compile(r"(CMBX|Bold|NimbusRomNo9L-Medi)", flags=re.IGNORECASE) #
    math_re     = re.compile(r"((CM)(SY|MI|EX)|math|Math|MSAM|MSBM|LASY|cmex|StandardSymL)", flags=re.IGNORECASE)
    #normal_re   = re.compile(r"(Times-Roman|CMR|CMTT|EUFM|NimbusRomNo9L-Regu|LMRoman[0-9]+-Regular)")

    fonts = {}

    for font in xml.findall(f".//{ALTO}TextStyle"):
        family = font.get("FONTFAMILY")
        id     = font.get("ID")
        size   = float(font.get("FONTSIZE"))

        is_italic   = italic_re.search(family) is not None
        is_math     = math_re.search(family) is not None
        is_bold     = bold_re.search(family) is not None

        fonts[id] = Font(is_italic, is_math, is_bold, size)

        #print(family, "=>", fonts[id])

    return fonts

def line_delta_v(line):
    block = line.getparent() # TextBlock
    line_index = block.index(line)

    if line_index > 0:
        previous_line      = block[line_index - 1]
        previous_line_v    = float(previous_line.get("VPOS")) + float(previous_line.get("HEIGHT"))
    else:
        previous_line_v    = 0.

    line_v = float(line.get("VPOS"))
    
    if line_v >= previous_line_v: # normal flow
        return line_v - previous_line_v
    else: # column break
        return -50
    
def line_delta_h(line):
    block   = line.getparent()
    line_h  = float(line.get("HPOS"))
    block_h = float(block.get("HPOS")) 
    return line_h - block_h

def get_features(word, fonts):
    text = word.get("CONTENT")
    font = word.get("STYLEREFS")

    line = word.getparent() # TextLine
    block   = line.getparent() # TextBlock
    line_words = line.findall(f"{ALTO}String")
    word_index = line_words.index(word)

    ft_delta_v = line_delta_v(line)

    if word_index > 0:
        previous_word   = line_words[word_index - 1]
        previous_word_h = float(previous_word.get("HPOS")) + float(previous_word.get("WIDTH"))
    else:
        previous_word_h = float(block.get("HPOS"))

    word_h      = float(word.get("HPOS"))
    # FEATURE: Distance with previous word.
    ft_delta_h  = word_h - previous_word_h 
    # FEATURE: Is first word of sentence.
    ft_first_word_of_line = word_index == 0

    # FEATURE: Word length
    ft_len  = len(text)
    # FEATURE: Is italic
    ft_ital = fonts[font].is_italic
    # FEATURE: Is formula
    ft_math = fonts[font].is_math
    # FEATURE: Is bold
    ft_bold = fonts[font].is_bold
    # FEATURE: Font size
    ft_fontsize = fonts[font].size
    # FEATURE: Word is heading
    ft_theorem = "theorem" in text.lower()
    ft_proposition = "proposition" in text.lower()
    ft_lemma = "lemma" in text.lower()
    ft_definition = "definition" in text.lower()
    # FEATURE: Word is "Proof"
    ft_proof   = "proof" in text.lower()
    # FEATURE: First letter is capital
    if len(text) > 0:
        ft_capital = 'A' <= text[0] <= 'Z'
    else:
        ft_capital = False
    
    return {
        "delta_v": ft_delta_v, "delta_h": ft_delta_h, 
        "first_word": ft_first_word_of_line, "length": ft_len, "italic": ft_ital, 
        "math": ft_math, "bold": ft_bold, "theorem": ft_theorem, "proposition": ft_proposition,
        "lemma": ft_lemma, "definition": ft_definition,
        "proof": ft_proof, "capital": ft_capital, "fontsize": ft_fontsize}

def get_line_features(line, fonts):
    words = line.findall(f".//{ALTO}String")

    ft_n_words = len(words)
    ft_delta_v = line_delta_v(line)
    ft_delta_h = line_delta_h(line)

    ft_mean_length  = 0
    ft_mean_math    = 0
    ft_mean_italic  = 0
    ft_mean_fontsize= 0

    first_word = True

    for word in words:
        word_features = get_features(word, fonts)

        if first_word:
            first_word = False

            ft_first_proof      = word_features["proof"]
            ft_first_definition = word_features["definition"]
            ft_first_theorem    = word_features["theorem"]
            ft_first_lemma      = word_features["lemma"]
            ft_first_proposition= word_features["proposition"]
            ft_first_capital    = word_features["capital"]
            ft_first_bold       = word_features["bold"]

        ft_mean_length  += word_features["length"] / ft_n_words
        ft_mean_math    += word_features["math"] / ft_n_words
        ft_mean_italic  += word_features["italic"] / ft_n_words
        ft_mean_fontsize+= word_features["fontsize"] / ft_n_words
    
    return {
        "delta_v": ft_delta_v,
        "delta_h": ft_delta_h,
        "mean_length": ft_mean_length,
        "mean_math": ft_mean_math,
        "mean_italic": ft_mean_italic,
        "mean_fontsize": ft_mean_fontsize,
        "first_proof": ft_first_proof,
        "first_definition": ft_first_definition,
        "first_theorem": ft_first_theorem,
        "first_lemma": ft_first_lemma,
        "first_proposition": ft_first_proposition, 
        "first_capital": ft_first_capital, 
        "first_bold": ft_first_bold, 
    }

def extract(xml, results: ResultsBoundingBoxes, mode="word"):
    """
    Build dataset from XML, either 'line'-based or 'word'-based.
    """

    if mode != "word" and mode != "line":
        print(f"Error: unknown extraction mode '{mode}''", file=sys.stderr)
        exit(1) 

    fonts    = extract_fonts(xml)

    entries = []
    kind, result_id = "Text", 0

    if mode == "word":
        node_query = f".//{ALTO}String"
    elif mode == "line":
        node_query = f".//{ALTO}TextLine"
    
    for node in xml.findall(node_query):
        if mode == "word":
            row = get_features(node, fonts)
            row["text"] = node.get("CONTENT")
        elif mode =="line":
            row = get_line_features(node, fonts)
            row["text"] = " ".join(word.get("CONTENT") for word in node.findall(f".//{ALTO}String"))

        old_kind, old_result_id = kind, result_id
        kind, result_id  = results.get_kind(node, mode="intersect")

        if old_kind == "Text":
            if kind != "Text":
                row["kind"] = "B-" + kind # Text -> Result
            else:
                row["kind"] = "O"         # Text -> Text
        else:
            if kind == old_kind and result_id == old_result_id: # Result -> Same result
                row["kind"] = "I-" + kind
            elif kind != "Text":             # Result -> Other result
                row["kind"] = "B-" + kind
            else:                            # Result -> Text
                row["kind"] = "O" 

        entries.append(row)
    
    # convert list of dicts to dict of lists.
    entries     = {key: [x[key] for x in entries] for key in entries[0].keys()}
    pd_entries  = pd.DataFrame.from_dict(entries) 
    return pd_entries

def process_paper(paper: Paper):
    parser      = ET.XMLParser(recover=True)
    if paper.results is not None and len(paper.results._data) > 0:
        xml     = ET.parse(f"{TARGET_PATH}/{paper.id}/{paper.id}.xml", parser=parser)
        entries = extract(xml, paper.results, mode=FEATURE_MODE)
        entries["from"] = paper.id
        return entries
    else:
        return None


