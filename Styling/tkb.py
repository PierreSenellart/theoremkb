#!/usr/bin/env python3

import sys, pickle, pandas as pd
from tqdm import tqdm
from joblib import Parallel, delayed  

from tools.config import DATA_PATH, FEATURE_MODE, ensuredir
from tools.theoremdb.db import TheoremDB
from tools.theoremdb.explorer import explorer
from tools.ml.features import process_paper
from tools.latex_extract.extract_theorems import run as extract_theorems
from tools.latex_extract.convert_to_xml import run as convert_to_xml
from tools.theoremdb.extract_graph import extract_graph
from tools.references.get_links import get_links

def usage():
    print("Usage:")
    print("tkb.py extract: extract theorem dataset from sources.")
    print("tkb.py db: build theorem database.")
    print("tkb.py explore: explore theorem database.")
    print("tkb.py ml: extract features.")
    print("tkb.py graph --name test --jobs 4 --chunksize 100: extract graph.")
    exit(1)


if len(sys.argv) == 1:
    usage()
elif sys.argv[1] == "extract":
    if len(sys.argv) == 3:
        pdf = sys.argv[2]
        extract_theorems([pdf])
        convert_to_xml([pdf])
    else:
        extract_theorems()
        convert_to_xml()
elif sys.argv[1] == "extract-step-2":
    convert_to_xml()
elif sys.argv[1] == "extract-step-1":
    if len(sys.argv) == 3:
        pdf = sys.argv[2]
        extract_theorems([pdf])
    else:
        extract_theorems()
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
elif sys.argv[1] == "graph":
    args_tab = sys.argv[2:]
    n = len(args_tab)
    args = [(args_tab[2*i],args_tab[2*i+1]) for i in range(n//2)]
    name = "test"
    jobs = 4
    chunksize = 100
    subfolder = ""
    for (k,v) in args:
        if k == "--sub":
            subfolder = v
        elif k == "--name":
            name = v
        elif k == "--jobs":
            jobs = int(v)
        elif k == "--chunksize":
            chunksize = int(v)
        else:
            raise ValueError
    extract_graph(name,True,jobs,chunksize,subfolder)
elif sys.argv[1] == "full":
    args_tab = sys.argv[2:]
    n = len(args_tab)
    args = [(args_tab[2*i],args_tab[2*i+1]) for i in range(n//2)]
    name = "test"
    jobs = -1
    chunksize = 100
    subfolder = ""
    for (k,v) in args:
        if k == "--sub":
            subfolder = v
        elif k == "--name":
            name = v
        elif k == "--jobs":
            jobs = int(v)
        elif k == "--chunksize":
            chunksize = int(v)
        else:
            raise ValueError

    print("Step 1 : Extract Theorems from sources")
    extract_theorems(subfolder)
    print("Step 2 : Convert pdf to xml with pdfalto")
    convert_to_xml(subfolder)
    print("Step 3 : Extract results and links between them")
    extract_graph(name,True,jobs,chunksize,subfolder)
    #print("Step 4 : Associate tags with other papers")
    #print("Step 5 : Build a graph of results")
elif sys.argv[1] == "links":
    args_tab = sys.argv[2:]
    n = len(args_tab)
    args = [(args_tab[2*i],args_tab[2*i+1]) for i in range(n//2)]
    subfolder = ""
    for (k,v) in args:
        if k == "--sub":
            subfolder = v
        else:
            raise ValueError
    get_links(subfolder)


else:
    usage()
