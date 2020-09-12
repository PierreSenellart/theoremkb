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
import random
from sklearn import metrics
import argparse
from sklearn.model_selection import train_test_split
from termcolor import colored
from joblib import Parallel, delayed

from multiprocessing import Pool

import faulthandler

faulthandler.enable()

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from lib.tkb import TheoremKB
from lib.extractors import TrainableExtractor
from lib.paper import AnnotationLayerInfo
from lib.misc.namespaces import *
from lib.config import SQL_ENGINE, TKB_VERSION
from lib.misc.bounding_box import BBX

session_factory = sessionmaker(bind=SQL_ENGINE)
Session = scoped_session(session_factory)


def register(args):
    print("REGISTER")
    tkb = TheoremKB()
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
    print("Added", added_papers, "papers!")


def remove(args):
    print("REMOVE")
    tkb = TheoremKB()
    session = Session()
    tkb.delete_paper(session, args.name)
    session.commit()
    print("removed " + args.name)


def split(args):
    print("SPLIT")
    tkb = TheoremKB()
    session = Session()

    groups = tkb.list_layer_groups(session)
    for group in filter(lambda x: x.name == args.group, groups):
        if args.test + args.validation > 0 and len(group.layers) > 0:
            layers_train, layers_test = train_test_split(
                group.layers, test_size=args.test + args.validation
            )
            if args.validation > 0:
                layers_val, layers_test = train_test_split(
                    layers_test, test_size=args.test / (args.test + args.validation)
                )
            else:
                layers_val = []
        else:
            layers_train = group.layers
            layers_test, layers_val = [], []

        for name, layers in [("train", layers_train), ("val", layers_val), ("test", layers_test)]:
            new_group_id = group.id + "." + name
            if tkb.get_layer_group(session, new_group_id) is None:
                tkb.add_layer_group(
                    session,
                    new_group_id,
                    group.name + "-" + name,
                    group.class_,
                    group.extractor,
                    group.extractor_info,
                )

            for layer in layers:
                layer.group_id = new_group_id
    session.commit()


def train(args):
    print("TRAIN")
    tkb = TheoremKB()
    session = Session()

    extractor = tkb.extractors[args.extractor]
    class_id = extractor.class_.name

    if args.layer is None:
        annotated_papers = filter(
            lambda x: x[1] is not None,
            map(
                lambda paper: (paper, paper.get_training_layer(class_id)), tkb.list_papers(session)
            ),
        )
        annotated_papers_train, annotated_papers_test = list(annotated_papers), []
    else:
        annotated_papers_train = []
        for paper in tkb.list_papers(session):
            for layer in paper.layers:
                if layer.name == args.layer and layer.class_ == class_id:
                    annotated_papers_train.append((paper, layer))
                    break

        annotated_papers_test = []
        if args.val_layer is not None:
            annotated_papers_test = []
            for paper in tkb.list_papers(session):
                for layer in paper.layers:
                    if layer.name == args.val_layer and layer.class_ == class_id:
                        annotated_papers_test.append((paper, layer))
                        break

    print(
        f"Training data: {len(annotated_papers_train)} (train)/ {len(annotated_papers_test)} (test)"
    )

    if isinstance(extractor, TrainableExtractor):
        extractor.train(annotated_papers_train, args)
    else:
        raise Exception("Not trainable.")
    print("Trained! Testing..")

    print("Train results:")
    test(args, args.layer)
    print("Test results:")
    test(args, args.val_layer)


def test(args, test_layer=None):
    print("TEST")
    tkb = TheoremKB()
    session = Session()

    if test_layer is None:
        test_layer = args.layer

    extractor = tkb.extractors[args.extractor]
    class_id = extractor.class_.name

    if test_layer is None:
        annotated_papers = list(
            filter(
                lambda x: x[1] is not None,
                map(
                    lambda paper: (paper, paper.get_training_layer(class_id)),
                    tkb.list_papers(session),
                ),
            )
        )
    else:
        annotated_papers = []
        for paper in tkb.list_papers(session):
            for layer in paper.layers:
                if layer.name == test_layer and layer.class_ == class_id:
                    annotated_papers.append((paper, layer))
                    break

    if args.n is not None:
        annotated_papers = annotated_papers[:args.n]

    def compare_layers(paper, true, pred):
        y = []
        y_pred = []

        for token in paper.get_xml().getroot().findall(f".//{ALTO}String"):
            bbx = BBX.from_element(token)
            y.append(true.get_label(bbx))
            y_pred.append(pred.get_label(bbx))
        return y, y_pred

    def test_paper(paper, layer, args):
        layer_pred = extractor.apply(paper, [], args)  # todo: parameters.
        layer_true = paper.get_annotation_layer(layer.id)
        return compare_layers(paper, layer_true, layer_pred)

    args.func=None
    if args.single_core:
        res = [test_paper(paper, layer, args) for paper, layer in tqdm(annotated_papers)]
    else:
        res = Parallel(n_jobs=-1)(
            delayed(test_paper)(paper, layer, args) for paper, layer in tqdm(annotated_papers)
        )

    y, y_pred = [], []
    for y_paper, y_pred_paper in res:
        y.extend(y_paper)
        y_pred.extend(y_pred_paper)

    sorted_labels = sorted(extractor.class_.labels)
    print(metrics.classification_report(y, y_pred, labels=sorted_labels, digits=3))


def process_paper(x):
    (group_id, paper_id, name, extractor) = x

    tkb = TheoremKB()
    session = Session()
    paper = tkb.get_paper(session, paper_id)

    for layer in paper.layers:
        if layer.name == name and layer.class_ == extractor.class_.name:
            print("skipped.", end="")
            return

    if paper.id in set(["1709.05182"]):
        return

    print(">>", paper_id)

    try:
        extractor.apply_and_save(paper, [], group_id)
        if extractor.class_.name == "header":
            paper.title = "__undef__"
        session.commit()
        session.close()
    except Exception as e:
        print(paper.id, "failed")
        print(e)
        tb = traceback.format_exc()
        print(tb)


def apply(args):
    print("APPLY")
    tkb = TheoremKB()
    session = Session()
    papers = tkb.list_papers(session)
    paper_ids = [str(p.id) for p in tqdm(papers)]

    extractor = tkb.extractors[args.extractor]

    group_id = shortuuid.uuid()

    tkb.add_layer_group(
        session,
        group_id,
        args.name,
        extractor.class_.name,
        extractor.name,
        extractor.description,
    )

    session.commit()
    session.flush()
    session.close()

    if args.single_core:
        for id in tqdm(paper_ids):
            process_paper((group_id, id, args.name, extractor))

    else:
        with Pool(7) as p:
            p.map(process_paper, [(group_id, id, args.name, extractor) for id in paper_ids])


def bench(args):
    print("BENCH")
    tkb = TheoremKB()
    extractor = tkb.extractors[args.extractor]
    layer_ = extractor.class_

    session = Session()

    t0 = time.time()
    paper = tkb.get_paper(session, args.paper)

    extractor.apply_and_save(paper, "bench")
    t1 = time.time()
    print("Result: {:4f}".format(t1 - t0))


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
    tkb = TheoremKB()

    def process_paper(paper):
        try:
            paper._build_features(force=True)
        except Exception as e:
            print(paper.id, "failed:", e)

    Parallel(n_jobs=-1)(delayed(process_paper)(paper) for paper in tqdm(tkb.list_papers(session)))


def info(args):
    tkb = TheoremKB()
    extractor = tkb.extractors[args.extractor]
    print(args.extractor, ":")
    print(extractor.description)
    extractor.info()

def cleanup(_):
    session = Session()
    tkb = TheoremKB()

    gdict = {}

    c = 0    

    for group in tkb.list_layer_groups(session):
        key = group.name, group.class_
        if key in gdict:
            c += 1
            for layer in group.layers:
                layer.group_id = gdict[key]
            session.delete(group)
        else:
            if len(group.layers) == 0:
                session.delete(group)
            else:
                gdict[key] = group.id
    print(c)
    session.commit() 

def summary(_):
    session = Session()
    tkb = TheoremKB()

    print(colored("# Layer:", attrs=["bold"]))
    for class_ in tkb.classes.values():
        print("> ", class_.name, ": ", ",".join(class_.labels), sep="")
    print()
    print(colored("# Extractors:", attrs=["bold"]))
    for name, ex in tkb.extractors.items():
        if isinstance(ex, TrainableExtractor):
            print(
                "> {:28}".format(name),
                colored(" (trained)", "green") if ex.is_trained else colored("(untrained)", "red"),
                sep="",
            )
        else:
            print("> ", name, sep="")
    print()
    print(colored("# Papers:", attrs=["bold"]), colored(len(tkb.list_papers(session)), "green"))
    print()
    print("# Groups:")
    for group in tkb.list_layer_groups(session):
        print(group.class_, group.name, len(group.layers))

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.set_defaults(func=summary)
    subparsers = parser.add_subparsers()

    # train
    parser_train = subparsers.add_parser("train")
    subparsers_train = parser_train.add_subparsers(dest="extractor")
    subparsers_train.required = True

    for extractor_name, extractor in TheoremKB().extractors.items():
        if isinstance(extractor, TrainableExtractor):
            parser_extractor = subparsers_train.add_parser(extractor_name)
            extractor.add_args(parser_extractor)
            extractor.add_train_args(parser_extractor)

    parser_train.add_argument(
        "-l", "--layer", type=str, default=None, help="Take all layers that have given name."
    )
    parser_train.add_argument(
        "-v", "--val_layer", type=str, default=None, help="Use this group for validation."
    )

    parser_train.add_argument("-n", type=int, default=None)
    parser_train.add_argument("-s", "--single-core", action="store_true")
    parser_train.set_defaults(func=train)

    # split
    parser_split = subparsers.add_parser("split")
    parser_split.add_argument("group")
    parser_split.add_argument("-t", "--test", type=float, default=0)
    parser_split.add_argument("-v", "--validation", type=float, default=0)
    parser_split.set_defaults(func=split)

    # test
    parser_test = subparsers.add_parser("test")
    
    parser_test.add_argument("-n", type=int, default=None)
    parser_test.add_argument("-l", "--layer", type=str, default=None)
    parser_test.add_argument("-s", "--single-core", action="store_true")

    subparsers_test = parser_test.add_subparsers(dest="extractor")
    subparsers_test.required = True
    for extractor_name, extractor in TheoremKB().extractors.items():
        parser_extractor = subparsers_test.add_parser(extractor_name)
        extractor.add_args(parser_extractor)
    
    parser_test.set_defaults(func=test)

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

    # features
    parser_features = subparsers.add_parser("features")
    parser_features.set_defaults(func=features)

    # apply
    parser_apply = subparsers.add_parser("apply")
    parser_apply.add_argument("extractor", type=str)
    parser_apply.add_argument("name", type=str)
    parser_apply.add_argument("-s", "--single-core", action="store_true")
    parser_apply.set_defaults(func=apply)

    # bench
    parser_bench = subparsers.add_parser("bench")
    parser_bench.add_argument("extractor", type=str)
    parser_bench.add_argument("paper", type=str)
    parser_bench.set_defaults(func=bench)

    # delete
    parser_delete = subparsers.add_parser("delete")
    parser_delete.add_argument("class_id", type=str)
    parser_delete.add_argument("name", type=str)
    parser_delete.set_defaults(func=delete)

    # cleanup
    parser_cleanup = subparsers.add_parser("cleanup")
    parser_cleanup.set_defaults(func=cleanup)

    args = parser.parse_args(sys.argv[1:])
    args.func(args)

Session.remove()
