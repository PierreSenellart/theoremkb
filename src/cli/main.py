import sys
import os, time
from typing import Optional, List
from tqdm import tqdm
import lxml.etree as ET
from joblib import Parallel, delayed  
import shortuuid
from sqlalchemy.orm import Session
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
import traceback

import argparse

from multiprocessing import Pool

import faulthandler; faulthandler.enable()

sys.path.append(os.path.join(os.path.dirname(__file__),".."))
from lib.tkb import TheoremKB
from lib.extractors import TrainableExtractor, ALL_EXTRACTORS
from lib.paper import AnnotationLayerInfo
from lib.misc.namespaces import *
from lib.config import SQL_ENGINE

session_factory = sessionmaker(bind=SQL_ENGINE)
Session = scoped_session(session_factory)


def register(args):
    print("REGISTER")
    tkb=TheoremKB()
    session = Session()
    added_papers = 0

    for dirpath, _, filenames in tqdm(os.walk(args.path)):
        for paper_pdf in filenames:
            if not paper_pdf.lower().endswith(".pdf"):
                continue

            base_name = paper_pdf[:-4]
            pdf_dir = os.path.abspath(dirpath) + "/" + paper_pdf

            tkb.add_paper(session, base_name, pdf_dir)
            added_papers += 1

    session.commit()
    print("Added",added_papers,"papers!")

def remove(args):
    print("REMOVE")
    tkb = TheoremKB()
    session = Session()
    tkb.delete_paper(session, args.name)
    session.commit()
    print("removed "+args.name)

def train(args):
    print("TRAIN")
    tkb = TheoremKB()
    session = Session()

    extractor=tkb.extractors[args.extractor]
    class_id=extractor.class_.name

    if args.layer is None:
        annotated_papers = filter(lambda x: x[1] is not None, 
                           map(lambda paper: (paper, paper.get_training_layer(class_id)), tkb.list_papers(session)))
    else:
        annotated_papers = []
        for paper in tkb.list_papers(session):
            for layer in paper.layers:
                if layer.name == args.layer and layer.class_ == class_id:
                    annotated_papers.append((paper, layer))
                    break
    

    if isinstance(extractor, TrainableExtractor):
        extractor.train(list(annotated_papers), args, verbose=True)
    else:
        raise Exception("Not trainable.") 

def process_paper(x):
    (paper_id, name, extractor) = x

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
        if extractor.class_ == "header":
            paper.title = "__undef__"
        session.commit()
    except Exception as e:
        print(paper.id,"failed")
        print(e)
        tb = traceback.format_exc()
        print(tb)

def apply(args):
    print("APPLY")
    tkb = TheoremKB()
    session = Session()
    papers = tkb.list_papers(session)
    session.close()

    extractor=tkb.extractors[args.extractor]

    with Pool(7) as p:
        p.map(process_paper, [(str(p.id), args.name, extractor) for p in tqdm(papers)])

def bench(args):
    print("BENCH")
    tkb = TheoremKB()
    extractor=tkb.extractors[args.extractor]
    layer_ = extractor.class_

    session = Session()

    t0 = time.time()
    paper = tkb.get_paper(session, args.paper)

    extractor.apply_and_save(paper, "bench")
    t1 = time.time()
    print("Result: {:4f}".format(t1-t0))

def delete(args):
    tkb = TheoremKB()

    session = Session()
    for p in tqdm(tkb.list_papers(session)):
        to_rm = None
        for l in p.layers:
            if l.name == args.name and l.class_ == args.class_id:
                to_rm = l.id
        if to_rm is not None:
            p.remove_annotation_layer(to_rm)
    session.commit()

def features(args):
    session = Session()
    tkb=TheoremKB()

    def process_paper(paper):
        try:
            paper._build_features()
        except Exception as e:
            print(paper.id,"failed:",e)

    Parallel(n_jobs=-1)(delayed(process_paper)(paper) for paper in tqdm(tkb.list_papers(session)))


def info(args):
    tkb = TheoremKB()
    extractor=tkb.extractors[args.extractor]
    extractor.info()

def summary(_):
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


    parser = argparse.ArgumentParser()
    parser.set_defaults(func=summary)
    subparsers = parser.add_subparsers()

    # train
    parser_train = subparsers.add_parser("train")
    subparsers_train = parser_train.add_subparsers(dest="extractor")

    for extractor_name, extractor in ALL_EXTRACTORS.items():
        if issubclass(extractor, TrainableExtractor):
            parser_extractor = subparsers_train.add_parser(extractor_name)
            extractor.parse_args(parser_extractor)
    
    parser_train.add_argument("-l", "--layer", type=str, default=None, help="Take all layers that have given name.")
    parser_train.set_defaults(func=train)

    # register
    parser_register = subparsers.add_parser("register")
    parser_register.add_argument("path", type=str)
    parser_register.set_defaults(func=register)

    # remove
    parser_remove = subparsers.add_parser("remove")
    parser_remove.add_argument("name", type=str)
    parser_remove.set_defaults(func=remove)

    # info
    parser_info = subparsers.add_parser("info")
    parser_info.add_argument("extractor", type=str)
    parser_info.set_defaults(func=info)

    # remove
    parser_remove = subparsers.add_parser("remove")
    parser_remove.add_argument("name", type=str)
    parser_remove.set_defaults(func=remove)

    # features
    parser_features = subparsers.add_parser("features")
    parser_features.set_defaults(func=features)

    # apply
    parser_apply = subparsers.add_parser("apply")
    parser_apply.add_argument("extractor", type=str)
    parser_apply.add_argument("name", type=str)
    parser_apply.set_defaults(func=apply)
    
    # bench
    parser_bench = subparsers.add_parser("bench")
    parser_bench.add_argument("extractor", type=str)
    parser_bench.add_argument("name", type=str)
    parser_bench.set_defaults(func=bench)
    
    # delete
    parser_delete = subparsers.add_parser("delete")
    parser_delete.add_argument("class_id", type=str)
    parser_delete.add_argument("name", type=str)
    parser_delete.set_defaults(func=delete)
    
    args = parser.parse_args(sys.argv[1:])
    args.func(args)

Session.remove()
