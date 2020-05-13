#!/bin/python3
import shutil,os,subprocess,re
from xml.etree import ElementTree as ET
from config import TARGET_PATH
from tqdm import tqdm
from joblib import Parallel, delayed  

# convert each pdf in a line-based text file.
# the xml is the raw output of pdfminer
# the txt is the filtered, line-by-line content.

def process_files(path,files):
    failed = []

    for file in files:
        if file.endswith(".pdf"):
            print(file)
            base = file.replace(".pdf","")

            xml_path = f"{path}/{base}.xml"

            if os.path.exists(xml_path):
                continue

            # convert to XML.
            result = subprocess.run(["pdfalto", "-readingOrder", "-blocks", "-annotation", f"{path}/{file}", xml_path])
            if result.returncode != 0:
                failed.append(file)
    return failed



res = Parallel(n_jobs=-1)(delayed(process_files)(path,files) for path,_,files in tqdm(list(os.walk(TARGET_PATH))))
with open("convert_to_xml.log", "w") as f:
    res = [item for sublist in res for item in sublist]
    print("FAILED:", ",".join(res), file=f)
