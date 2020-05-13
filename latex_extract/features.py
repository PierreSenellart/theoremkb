from collections import namedtuple
from lxml import etree as ET
import sys,os,re,pickle
from tqdm import tqdm
from joblib import Parallel, delayed  
import pandas as pd

from config import TARGET_PATH

ALTO = "{http://www.loc.gov/standards/alto/ns-v3#}"

def get_all_theorems(xml):
    theorems = []
    theorem = []
    for word in xml.findall(f".//{ALTO}String"):
        if word.get("CONTENT") == "***": 
            if len(theorem) > 0: # flush current theorem.
                theorems.append(theorem)
            theorem = [] # start new theorem.
        else: # add word to current theorem.
            theorem.append(word.get("CONTENT"))
    
    if len(theorem) > 0: # flush last theorem.
        theorems.append(theorem)
    
    return theorems

class TheoremBB:
    """
    Theorem bounding boxes container.
    """

    def __init__(self, xml_annot):
        """
        Parse an XML annotation file to gather theorems bounding boxes.
        """
        self._theorems = {}

        extthm_re = re.compile(r"uri:theorem\.Theorem\.([0-9]+)")

        BBX       = namedtuple("BBX", ["page_num", "min_h", "min_v", "max_h", "max_v"]) # the type for a bounding box.

        for annotation in xml_annot.findall(".//ANNOTATION/ACTION[@type='uri']/.."):
            dest = annotation.find("ACTION/DEST")
            link_theorem_match = extthm_re.search(dest.text)
            if link_theorem_match is None:
                continue

            theorem_number = int(link_theorem_match.group(1))

            if theorem_number not in self._theorems:
                self._theorems[theorem_number] = []

            page_num = annotation.get("pagenum")

            quadpoints = annotation.findall("QUADPOINTS/QUADRILATERAL/POINT")
            min_h, min_v, max_h, max_v = None, None, None, None
            for point in quadpoints:
                h, v = float(point.get("HPOS")), float(point.get("VPOS"))

                if min_h is None:
                    min_h, max_h = h, h
                    min_v, max_v = v, v
                else:
                    min_h = min(min_h, h)
                    max_h = max(max_h, h)
                    min_v = min(min_v, v)
                    max_v = max(max_v, v)
            
            self._theorems[theorem_number].append(BBX(page_num, min_h, min_v, max_h, max_v))

    def is_in_theorem(self, node):
        """
        Check if a node, containing HPOS, VPOS, HEIGHT, WIDTH fields, is in a theorem or not.
        """
        min_h, min_v = float(node.get("HPOS")), float(node.get("VPOS"))
        max_h, max_v = min_h + float(node.get("WIDTH")), min_v + float(node.get("HEIGHT"))

        while node.tag != f"{ALTO}Page":
            node = node.getparent()
        page_num     = node.get("PHYSICAL_IMG_NR")
        
        for bbxes in self._theorems.values():
            for bbx in bbxes:
                if page_num == bbx.page_num and min_h >= bbx.min_h and min_v >= bbx.min_v and max_h <= bbx.max_h and max_v <= bbx.max_v:
                    return True

        return False

    def __len__(self):
        return len(self._theorems)

def extract_fonts(xml):
    Font = namedtuple("Font", ["is_italic", "is_math", "is_bold"])

    italic_re   = re.compile(r"((TI)[0-9]+|Ital|rsfs|EUSM)", flags=re.IGNORECASE)
    bold_re     = re.compile(r"(CMBX|Bold|NimbusRomNo9L-Medi)", flags=re.IGNORECASE) #
    math_re     = re.compile(r"((CM)(SY|MI|EX)|math|Math|MSAM|MSBM|LASY|cmex|StandardSymL)", flags=re.IGNORECASE)
    #normal_re   = re.compile(r"(Times-Roman|CMR|CMTT|EUFM|NimbusRomNo9L-Regu|LMRoman[0-9]+-Regular)")

    fonts = {}

    for font in xml.findall(f".//{ALTO}TextStyle"):
        family = font.get("FONTFAMILY")
        id     = font.get("ID")

        is_italic   = italic_re.search(family) is not None
        is_math     = math_re.search(family) is not None
        is_bold     = bold_re.search(family) is not None

        fonts[id] = Font(is_italic, is_math, is_bold)

        #print(family, "=>", fonts[id])

    return fonts

heading_re  = re.compile(r"(Theorem|Lemma|Claim|Corollary|Proposition|Fact)")
proof_re    = re.compile(r"Proof")

def get_features(word, fonts):
    text = word.get("CONTENT")
    font = word.get("STYLEREFS")

    line = word.getparent()
    line_words = line.findall(f"{ALTO}String")
    word_index = line_words.index(word)

    block = line.getparent()
    line_index = block.index(line)

    if line_index > 0:
        previous_line      = block[line_index - 1]
        previous_line_v    = float(previous_line.get("VPOS")) + float(previous_line.get("HEIGHT"))
    else:
        previous_line_v    = 0.

    line_v = float(line.get("VPOS"))
    # FEATURE: Distance with previous line.
    if line_v > previous_line_v: # normal flow
        ft_delta_v = line_v - previous_line_v
    else: # column break
        ft_delta_v = line_v

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
    # FEATURE: Word is heading
    ft_heading = heading_re.search(text) is not None
    # FEATURE: Word is "Proof"
    ft_proof   = proof_re.search(text) is not None
    # FEATURE: First letter is capital
    if len(text) > 0:
        ft_capital = 'A' <= text[0] <= 'Z'
    else:
        ft_capital = False
    
    return {"delta_v": ft_delta_v, "delta_h": ft_delta_h, 
        "first_word": ft_first_word_of_line, "len": ft_len, "italic": ft_ital, 
        "math": ft_math, "bold": ft_bold, "heading": ft_heading, 
        "proof": ft_proof, "capital": ft_capital}


def extract(xml, xml_annot):
    theorems = TheoremBB(xml_annot)
    fonts    = extract_fonts(xml)

    entries = []


    for word in xml.findall(f".//{ALTO}String"):

        row            = get_features(word, fonts)
        row["text"]    = word.get("CONTENT")
        row["theorem"] = theorems.is_in_theorem(word)

        entries.append(row)
    
    # convert list of dicts to dict of lists.
    entries     = {key: [x[key] for x in entries] for key in entries[0].keys()}
    pd_entries  = pd.DataFrame.from_dict(entries) 
    return pd_entries, [len(x) for x in theorems._theorems.values()]

def process_paper(paper):
    parser    = ET.XMLParser(recover=True)
    if os.path.exists(f"{TARGET_PATH}/{paper}/{paper}.xml"):
        xml       = ET.parse(f"{TARGET_PATH}/{paper}/{paper}.xml", parser=parser)
        xml_annot = ET.parse(f"{TARGET_PATH}/{paper}/{paper}_annot.xml", parser=parser)
        
        entries, theorems_lengths = extract(xml, xml_annot)

        if len(theorems_lengths) == 0: # Ignore whole paper if no theorems have been found.
            return paper, "No theorem", None, []
        else:
            entries["from"] = paper
            return paper, "OK", entries, theorems_lengths
    else:
        return paper, "No XML", None, []


res = Parallel(n_jobs=-2)(delayed(process_paper)(dir) for dir in tqdm(list(os.listdir(TARGET_PATH))))


dataframes = []
results    = {}
theorems   = {}

for x in res: # (paper, result, dataframe, theorems_lengths)
    if x[2] is not None:
        dataframes.append(x[2])

    if x[1] not in results:
        results[x[1]] = 0
    results[x[1]] += 1
    
    theorems[x[0]] = (x[1], x[3]) 

for k,v in results.items():
    print(k, ": ", v, sep="")

df = pd.concat(dataframes, ignore_index=True)
df.to_pickle("09-05-features.pkl")

with open("09-05-features-log.pkl", "wb") as f:
    pickle.dump(theorems, f)
