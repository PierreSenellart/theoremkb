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
from ..theoremdb.links import RefsBBX

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
        page = block.getparent() # PrintSpace
        block_index = page.index(block)
        if block_index > 0:
            previous_block     = page[block_index - 1]
            previous_line_v    = float(previous_block.get("VPOS")) + float(previous_block.get("HEIGHT"))
        else:
            previous_line_v    = 0

    line_v = float(line.get("VPOS"))
    
    if line_v >= previous_line_v: # normal flow
        return line_v - previous_line_v
    else: # column break
        return 0
    
def line_delta_h(line):
    block   = line.getparent()
    line_h  = float(line.get("HPOS"))
    block_h = float(block.get("HPOS")) 
    return line_h - block_h

def line_next_delta_h(line):
    block   = line.getparent()
    line_h  = float(line.get("HPOS")) + float(line.get("WIDTH"))
    block_h = float(block.get("HPOS")) + float(block.get("WIDTH")) 
    return block_h - line_h


def get_features(word, fonts):
    text = word.get("CONTENT")
    font = word.get("STYLEREFS")

    line = word.getparent() # TextLine
    block   = line.getparent() # TextBlock
    line_words = line.findall(f"{ALTO}String")
    word_index = line_words.index(word)

    # FEATURE: Distance with previous line.
    ft_delta_v = line_delta_v(line)

    if word_index > 0:
        previous_word   = line_words[word_index - 1]
        previous_word_h = float(previous_word.get("HPOS")) + float(previous_word.get("WIDTH"))
    else:
        previous_word_h = float(block.get("HPOS"))

    if word_index < len(line_words) - 1:
        next_word       = line_words[word_index + 1]
        next_word_h     = float(next_word.get("HPOS"))
    else:
        next_word_h     = float(block.get("HPOS")) + float(block.get("WIDTH"))

    word_h      = float(word.get("HPOS"))
    word_w      = float(word.get("WIDTH"))
    # FEATURE: Distance with previous word or with baseline.
    ft_delta_h  = word_h - previous_word_h
    # FEATURE: Distance with next word or with baseline.
    ft_next_delta_h = next_word_h - (word_h + word_w)
    # FEATURE: Is first word of line.
    ft_first_word_of_line = word_index == 0
    # FEATURE: Is last word of line. 
    ft_last_word_of_line  = word_index == len(line_words) - 1

    # FEATURE: Is italic
    ft_ital = fonts[font].is_italic
    # FEATURE: Is formula
    ft_math = fonts[font].is_math
    # FEATURE: Is bold
    ft_bold = fonts[font].is_bold
    # FEATURE: Font size
    ft_fontsize = fonts[font].size
    
    return {
        "delta_v": ft_delta_v, "delta_h": ft_delta_h, "next_delta_h": ft_next_delta_h, 
        "first_word": ft_first_word_of_line, "last_word": ft_last_word_of_line,
        "italic": ft_ital, "math": ft_math, "bold": ft_bold, "fontsize": ft_fontsize}

def get_line_features(line, fonts):
    words = line.findall(f".//{ALTO}String")

    ft_n_words = len(words)
    ft_delta_v = line_delta_v(line)
    ft_delta_h = line_delta_h(line)
    ft_next_delta_h = line_next_delta_h(line)

    ft_mean_math    = 0
    ft_mean_italic  = 0
    ft_mean_fontsize= 0

    for word in words:
        word_features = get_features(word, fonts)

        ft_mean_math    += word_features["math"] / ft_n_words
        ft_mean_italic  += word_features["italic"] / ft_n_words
        ft_mean_fontsize+= word_features["fontsize"] / ft_n_words
    
    return {
        "delta_v": ft_delta_v,
        "delta_h": ft_delta_h,
        "next_delta_h": ft_next_delta_h,
        "mean_math": ft_mean_math,
        "mean_italic": ft_mean_italic,
        "mean_fontsize": ft_mean_fontsize,
    }

def extract(xml, results: ResultsBoundingBoxes, refs: RefsBBX, mode="word",needlink=True):
    """
    Build dataset from XML, either 'line'-based or 'word'-based.
    """

    if mode != "word" and mode != "line":
        print(f"Error: unknown extraction mode '{mode}''", file=sys.stderr)
        exit(1) 

    fonts    = extract_fonts(xml)

    entries = []

    if mode == "word":
        node_query = f".//{ALTO}String"
    elif mode == "line":
        node_query = f".//{ALTO}TextLine"

    begin_ok = set()
    
    for node in xml.findall(node_query):
        if mode == "word":
            row = get_features(node, fonts)
            row["text"] = node.get("CONTENT")
        elif mode =="line":
            row = get_line_features(node, fonts)
            row["text"] = " ".join(word.get("CONTENT") for word in node.findall(f".//{ALTO}String"))

        kind, result_id  = results.get_kind(node)
        if needlink:
            is_link, link = refs.get_dest(node)
            row["is_link"] = is_link
            if is_link >= 0:
                row["page_dest"] = link["page_dest"]
                row["x_dest"]    = link["x_dest"]
                row["y_dest"]    = link["y_dest"]
            else:
                row["page_dest"] = None
                row["x_dest"] = None
                row["y_dest"] = None

        if kind == "Text":
            row["kind"] = "O" 
        elif result_id in begin_ok:
            row["kind"] = "I-" + kind
        else:
            begin_ok.add(result_id)
            row["kind"] = "B-" + kind
        row["result"] = result_id
        entries.append(row)
    
    # convert list of dicts to dict of lists.
    entries     = {key: [x[key] for x in entries] for key in entries[0].keys()}
    pd_entries  = pd.DataFrame.from_dict(entries) 
    return pd_entries

def process_paper(paper: Paper,mode="word",needlink=True):
    parser      = ET.XMLParser(recover=True)
    if paper.results is not None and len(paper.results._data) > 0:
        xml     = ET.parse(f"{TARGET_PATH}/{paper.id}/{paper.id}.xml", parser=parser)
        entries = extract(xml, paper.results, paper.refs, mode=mode,needlink=needlink)
        entries["from"] = paper.id
        return entries
    else:
        return None


