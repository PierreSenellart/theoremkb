#!/usr/bin/env python3

import sys, pickle, pandas as pd
from tqdm import tqdm
from joblib import Parallel, delayed  

from src.config import DATA_PATH, FEATURE_MODE, ensuredir
from src.theoremdb.db import TheoremDB
from src.theoremdb.explorer import explorer
from src.ml.features import process_paper

def usage():
    print("Usage:")
    print("tkb.py db: build theorem database.")
    print("tkb.py ex: explore theorem database.")
    print("tkb.py ml: extract features.")
    exit(1)


if len(sys.argv) == 1:
    usage()
elif sys.argv[1] == "db":
    db = TheoremDB()
    ensuredir(DATA_PATH)
    with open(f"{DATA_PATH}/papers_db.pkl", "wb") as f:
        pickle.dump(db, f)
elif sys.argv[1] == "ex":
    explorer()
elif sys.argv[1] == "ml":
    with open(f"{DATA_PATH}/papers_db.pkl", "rb") as f:
        db = pickle.load(f)

    res = Parallel(n_jobs=-2)(delayed(process_paper)(dir) for dir in tqdm(db.papers.values()))


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