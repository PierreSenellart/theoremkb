import sys, os, time, argparse, shortuuid
import lxml.etree as ET
from typing import Tuple
from tqdm import tqdm
from joblib import Parallel, delayed
from sqlalchemy.orm import Session
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sklearn import metrics
from sklearn.model_selection import train_test_split
from termcolor import colored
from joblib import Parallel, delayed
from multiprocessing import Pool

from lib.tkb import TheoremKB
from lib.extractors import Extractor, TrainableExtractor
from lib.paper import AnnotationLayerInfo
from lib.misc.namespaces import *
from lib.config import config
from lib.misc.bounding_box import BBX

session_factory = sessionmaker(bind=config.SQL_ENGINE)
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


def remove_tag(args):
    print("REMOVE")
    tkb = TheoremKB()
    session = Session()

    count = 0

    for tag in tkb.list_layer_tags(session):
        if tag.name == args.tag:
            session.delete(tag)
            count += 1

    session.commit()
    print(f"Removed {count} tags.")


def split(args):
    print("SPLIT")
    tkb = TheoremKB()
    session = Session()

    if args.test + args.validation == 0:
        print("No split to do (test == 0 && validation == 0)")
        return

    tags = tkb.list_layer_tags(session)

    for tag in filter(lambda x: x.name == args.tag, tags):
        if args.test + args.validation > 0 and len(tag.layers) > 0:
            layers_train, layers_test = train_test_split(
                tag.layers, test_size=args.test + args.validation
            )
            if args.validation > 0:
                layers_val, layers_test = train_test_split(
                    layers_test, test_size=args.test / (args.test + args.validation)
                )
            else:
                layers_val = []
        else:
            layers_train = tag.layers
            layers_test, layers_val = [], []

        for name, layers in [("train", layers_train), ("val", layers_val), ("test", layers_test)]:
            new_tag_id = shortuuid.uuid()

            if len(layers) == 0:  # skip if no layers are needed.
                continue

            tag_db = tkb.add_layer_tag(session, new_tag_id, f"{tag.name} ({name})", False, {})

            for layer in layers:
                layer.tags.append(tag_db)

    session.commit()


def train(args):
    print("TRAIN")
    tkb = TheoremKB()
    session = Session()

    extractor = tkb.extractors[args.extractor]
    class_id = extractor.class_.name

    annotated_papers_train = []
    for paper in tkb.list_papers(session):
        for layer in paper.layers:  # TODO: select the most recent layer.
            if any((tag.name == args.train_tag for tag in layer.tags)) and layer.class_ == class_id:
                annotated_papers_train.append((paper, layer))
                break

    annotated_papers_test = []
    if args.val_layer is not None:
        for paper in tkb.list_papers(session):
            for layer in paper.layers:
                if (
                    any((tag.name == args.val_tag for tag in layer.tags))
                    and layer.class_ == class_id
                ):
                    annotated_papers_test.append((paper, layer))
                    break

    if len(annotated_papers_train) == 0:
        print("No training layer found using this tag.")
        return

    print(
        f"Training data: {len(annotated_papers_train)} (train)/ {len(annotated_papers_test)} (test)"
    )

    if isinstance(extractor, TrainableExtractor):
        extractor.train(annotated_papers_train, args)
    else:
        print("The chosen extractor is not trainable.")

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

    annotated_papers = []
    for paper in tkb.list_papers(session):
        for layer in paper.layers:
            if any((tag.name == args.test_tag for tag in layer.tags)) and layer.class_ == class_id:
                annotated_papers.append((paper, layer))
                break

    if args.n is not None:
        annotated_papers = annotated_papers[: args.n]

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

    args.func = None
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


def process_paper(x: Tuple[str, str, str, Extractor]):
    (tag_id, paper_id, args, extractor) = x

    tkb = TheoremKB()
    session = Session()
    paper = tkb.get_paper(session, paper_id)

    for layer in paper.layers:
        if any((tag.name == args.name for tag in layer.tags)) and layer.class_ == extractor.class_.name:
            print("skipped.", end="")
            return

    if paper.id in set(["1709.05182"]):
        return

    print(">>", paper_id)

    tag = tkb.get_layer_tag(session, tag_id)

    try:
        new_layer = extractor.apply_and_save(paper, [], args)
        if extractor.class_.name == "header":
            paper.title = "__undef__"
        new_layer.tags.append(tag)
        
        session.commit()
        session.close()
    except Exception:
        print(paper.id, "failed")


def apply(args):
    print("APPLY")
    tkb = TheoremKB()
    session = Session()
    papers = tkb.list_papers(session)
    paper_ids = [str(p.id) for p in tqdm(papers)]

    extractor = tkb.extractors[args.extractor]

    tag_id = shortuuid.uuid()
    if args.name:
        tag_name = args.name
    else:
        tag_name = "from " + extractor.name
    
    tkb.add_layer_tag(
        session,
        tag_id,
        tag_name,
        False,
        {"extractor": {
            "name": extractor.name,
            "desc": extractor.description
        }}
    )

    session.commit()
    session.flush()
    session.close()

    args.func = None

    if args.single_core:
        for id in tqdm(paper_ids):
            process_paper((tag_id, id, args, extractor))
    else:
        with Pool(7) as p:
            p.map(process_paper, [(tag_id, id, args, extractor) for id in paper_ids])


def bench(args):
    print("BENCH")
    session = Session()
    tkb = TheoremKB()

    extractor = tkb.extractors[args.extractor]

    t0 = time.time()
    paper = tkb.get_paper(session, args.paper)

    extractor.apply_and_save(paper, "bench")
    t1 = time.time()
    print("Result: {:4f}".format(t1 - t0))


def features(args):
    session = Session()
    tkb = TheoremKB()

    def process_paper(paper):
        try:
            paper._build_features(force=True)
        except Exception as e:
            print(paper.id, "failed:", e)

    Parallel(n_jobs=-1)(delayed(process_paper)(paper) for paper in tqdm(tkb.list_papers(session)))

def title(args):
    session = Session()
    tkb = TheoremKB()

    def process_paper(paper_id):
        session = Session()
        tkb = TheoremKB()
        paper = tkb.get_paper(session, paper_id)
        if paper.title == "__undef__":
            paper._refresh_title()
        session.commit()
        session.close()

    paper_ids = [paper.id for paper in tkb.list_papers(session)]
    session.close()

    Parallel(n_jobs=1)(delayed(process_paper)(paper) for paper in tqdm(paper_ids))

def info(args):
    tkb = TheoremKB()
    extractor = tkb.extractors[args.extractor]
    print(args.extractor, ":")
    print(extractor.description)
    extractor.info()


def cleanup(_):
    session = Session()
    tkb = TheoremKB()

    c = 0

    for tag in tkb.list_layer_tags(session):
        if len(tag.layers) == 0 and not tag.readonly:
            session.delete(tag)
            c += 1
        
    print(f"Removed {c} tags.")
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
    print(colored("# Tags:", attrs=["bold"]))
    for tag, counts in tkb.count_layer_tags(session).values():
        if tag.readonly:
            print(">", colored(f"{tag.name:28}", "yellow"), "| ", end="")
        else:
            print(f"> {tag.name:28}", "| ", end="")
        print((" " * 31 + "| ").join([f"{n:12} -> {c:6}\n" for n, c in counts.items()]))
    print()


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

    parser_train.add_argument("train-tag", type=str, help="Take all layers that have given tag.")
    parser_train.add_argument(
        "-v", "--val-tag", type=str, default=None, help="Use this tag for validation."
    )

    parser_train.add_argument("-n", type=int, default=None)
    parser_train.add_argument("-s", "--single-core", action="store_true")
    parser_train.set_defaults(func=train)

    # split
    parser_split = subparsers.add_parser("split")
    parser_split.add_argument("tag")
    parser_split.add_argument("-t", "--test", type=float, default=0)
    parser_split.add_argument("-v", "--validation", type=float, default=0)
    parser_split.set_defaults(func=split)

    # test
    parser_test = subparsers.add_parser("test")
    parser_test.add_argument("test-tag", type=str)
    parser_test.add_argument("-n", type=int, default=None)
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
    parser_remove = subparsers.add_parser("remove-tag")
    parser_remove.add_argument("tag", type=str)
    parser_remove.set_defaults(func=remove_tag)

    # info
    parser_info = subparsers.add_parser("info")
    parser_info.add_argument("extractor", type=str)
    parser_info.set_defaults(func=info)

    # features
    parser_features = subparsers.add_parser("features")
    parser_features.set_defaults(func=features)

    # title
    parser_title = subparsers.add_parser("title")
    parser_title.set_defaults(func=title)

    # apply
    parser_apply = subparsers.add_parser("apply")
    parser_apply.add_argument("extractor", type=str)
    parser_apply.add_argument("-n", "--name", type=str, default=None)
    parser_apply.add_argument("-s", "--single-core", action="store_true")
    parser_apply.set_defaults(func=apply)

    # bench
    parser_bench = subparsers.add_parser("bench")
    parser_bench.add_argument("extractor", type=str)
    parser_bench.add_argument("paper", type=str)
    parser_bench.set_defaults(func=bench)

    # cleanup
    parser_cleanup = subparsers.add_parser("cleanup")
    parser_cleanup.set_defaults(func=cleanup)

    args = parser.parse_args(sys.argv[1:])
    args.func(args)

Session.remove()
