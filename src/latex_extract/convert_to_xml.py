#!/bin/python3
import shutil,os,subprocess,re
from xml.etree import ElementTree as ET
from ..config import TARGET_PATH, LOGS_PATH, REGENERATE
from tqdm import tqdm
from joblib import Parallel, delayed  
from datetime import datetime

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

            if os.path.exists(xml_path) and not REGENERATE:
                continue

            # convert to XML.
            result = subprocess.run(["pdfalto", "-readingOrder", "-blocks", "-annotation", f"{path}/{file}", xml_path])
            if result.returncode != 0:
                failed.append(file)
    return failed

def run(subfolder=None):
    if subfolder != None:
        TARGET_PATH += '/'+subfolder
        LOGS_PATH += '/'+subfolder
        
    res = Parallel(n_jobs=-1)(delayed(process_files)(path,files) for path,_,files in tqdm(list(os.walk(TARGET_PATH))))

    date = datetime.now().strftime("%d-%m")

    with open(f"{LOGS_PATH}/{date}-pdf-to-xml.log", "w") as f:
        res = [item for sublist in res for item in sublist]
        print("FAILED:", ",".join(res), file=f)


if __name__ == "__main__":
    run()
