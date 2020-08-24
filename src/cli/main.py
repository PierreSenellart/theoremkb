import sys
import os, time
from typing import Optional
from tqdm import tqdm
import lxml.etree as ET
from joblib import Parallel, delayed  
import shortuuid
from sqlalchemy.orm import Session
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
import traceback

from multiprocessing import Pool

import faulthandler; faulthandler.enable()

sys.path.append("..")
from lib.tkb import TheoremKB
from lib.extractors import TrainableExtractor
from lib.paper import AnnotationLayerInfo
from lib.misc.namespaces import *
from lib.config import SQL_ENGINE

session_factory = sessionmaker(bind=SQL_ENGINE)
Session = scoped_session(session_factory)


def register(tkb: TheoremKB, path_pdf: str):
    session = Session()
    added_papers = 0

    for dirpath, _, filenames in tqdm(os.walk(path_pdf)):
        for paper_pdf in filenames:
            if not paper_pdf.lower().endswith(".pdf"):
                continue

            base_name = paper_pdf[:-4]
            pdf_dir = os.path.abspath(dirpath) + "/" + paper_pdf

            tkb.add_paper(session, base_name, pdf_dir)
            added_papers += 1

    session.commit()
    print("Added",added_papers,"papers!")

def remove(tkb: TheoremKB, name: str):
    session = Session()
    tkb.delete_paper(session, name)
    session.commit()
    print("removed "+name)

def train(tkb: TheoremKB, extractor_id: str):
    session = Session()

    extractor=tkb.extractors[extractor_id]
    class_id=extractor.class_.name
    annotated_papers = filter(lambda x: x[1] is not None, 
                        map(lambda paper: (paper, paper.get_training_layer(class_id)), tkb.list_papers(session)))

    if isinstance(extractor, TrainableExtractor):
        extractor.train(list(annotated_papers), verbose=True)
    else:
        raise Exception("Not trainable.") 
    

def test(tkb: TheoremKB, extractor_id: str, paper_id: str):
    session = Session()
    extractor=tkb.extractors[extractor_id]
    paper=tkb.get_paper(session, paper_id)

    annotated = extractor.apply(paper)
    reduced  = annotated.reduce()
    reduced.save('test.json')

def apply(tkb: TheoremKB, extractor_id: str, name: str):

    extractor=tkb.extractors[extractor_id]
    layer_ = extractor.class_

    session = Session()
    papers = tkb.list_papers(session)
    session.close()

    def process_paper(x):
        (i, paper_id) = x
        session = Session()
        paper = tkb.get_paper(session, paper_id)

        for layer in paper.layers:
            if layer.name == name:
                return
        
        if paper.id in set(["1709.05182"]):
            return

        print(">>", paper_id)

        try:
            extractor.apply_and_save(paper, name)
            session.commit()
        except Exception as e:
            print(paper.id,"failed")
            print(e)
            tb = traceback.format_exc()
            print(tb)
            
    for i,p in enumerate(tqdm(papers)):
        process_paper((i,str(p.id)))

def bench(extractor_id: str, paper_id: str):
    tkb = TheoremKB()
    extractor=tkb.extractors[extractor_id]
    layer_ = extractor.class_


    session = Session()

    t0 = time.time()
    paper = tkb.get_paper(session, paper_id)

    extractor.apply_and_save(paper, "bench")
    t1 = time.time()
    print("Result: {:4f}".format(t1-t0))


def info(tkb: TheoremKB, extractor_id: str):
    extractor=tkb.extractors[extractor_id]
    extractor.info()

def summary():
    session = Session()
    tkb = TheoremKB()

    print("# Layer: ")
    for class_ in tkb.classes.values():
        print("> ", class_.name,": ", ",".join(class_.labels), sep="")

    print("# Extractors:")
    for extra in tkb.extractors.keys():
        print("> ", extra, sep="")
    print("# Papers:", len(tkb.list_papers(session)))


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        summary()
        exit(1)

    if sys.argv[1] == "register" and len(sys.argv) > 2:
        path_pdf=sys.argv[2]

        tkb=TheoremKB()

        register(tkb, path_pdf)
    elif sys.argv[1] == "remove" and len(sys.argv) > 2:
        tkb=TheoremKB()
        remove(tkb, sys.argv[2])

    elif sys.argv[1] == "train" and len(sys.argv) > 2:
        extractor=sys.argv[2]

        tkb=TheoremKB()

        train(tkb, extractor)
    elif sys.argv[1] == "test" and len(sys.argv) > 3:
        layer=sys.argv[2]
        paper=sys.argv[3]

        tkb=TheoremKB()

        test(tkb, layer, paper)
    
    elif sys.argv[1] == "info" and len(sys.argv) > 2:
        layer=sys.argv[2]
        tkb=TheoremKB()
        info(tkb, layer)
    
    elif sys.argv[1] == "features":
        session = Session()
        tkb=TheoremKB()

        def process_paper(paper):
            try:
                paper._build_features()
            except Exception as e:
                print(paper.id,"failed:",e)

        Parallel(n_jobs=-1)(delayed(process_paper)(paper) for paper in tqdm(tkb.list_papers(session)))

    elif sys.argv[1] == "apply" and len(sys.argv) > 3:
        tkb=TheoremKB()
        layer=sys.argv[2]
        name=sys.argv[3]

        apply(tkb, layer, name)
    elif sys.argv[1] == "bench" and len(sys.argv) > 3:
        layer=sys.argv[2]
        paper=sys.argv[3]
        bench(layer, paper)

print("ok.")
Session.remove()