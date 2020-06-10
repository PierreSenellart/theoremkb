#!/usr/bin/env python3

import sys, pickle, pandas as pd
from tqdm import tqdm
from joblib import Parallel, delayed  

from src.config import DATA_PATH, FEATURE_MODE, ensuredir
from src.theoremdb.db import TheoremDB
from src.theoremdb.explorer import explorer
from src.ml.features import process_paper
from src.latex_extract.extract_theorems import run as extract_theorems
from src.latex_extract.convert_to_xml import run as convert_to_xml

def usage():
    print("Usage:")
    print("tkb.py extract: extract theorem dataset from sources.")
    print("tkb.py db: build theorem database.")
    print("tkb.py explore: explore theorem database.")
    print("tkb.py ml: extract features.")
    exit(1)


if len(sys.argv) == 1:
    usage()
elif sys.argv[1] == "extract":
    extract_theorems()
    convert_to_xml()
elif sys.argv[1] == "extract-step-2":
    convert_to_xml()
elif sys.argv[1] == "db":
    db = TheoremDB()
    ensuredir(DATA_PATH)
    with open(f"{DATA_PATH}/papers_db.pkl", "wb") as f:
        pickle.dump(db, f)
elif sys.argv[1] == "explore":
    explorer()
elif sys.argv[1] == "ml":
    with open(f"{DATA_PATH}/papers_db.pkl", "rb") as f:
        db = pickle.load(f)

    if len(sys.argv) > 2:
        count = int(sys.argv[2])
    else:
        count = len(db.papers)

    res = Parallel(n_jobs=-2)(delayed(process_paper)(dir) for dir in tqdm(list(db.papers.values())[:count]))


    documents  = []
    dataframes = []

    for x in res: # (dataframe, document_metadata)
        if x is not None:
            dataframes.append(x)
        documents.append(x)

    df = pd.concat(dataframes, ignore_index=True)
    df.to_pickle(f"{DATA_PATH}/features-{FEATURE_MODE}.pkl")
else:
    usage()
