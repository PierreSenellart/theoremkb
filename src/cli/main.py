import sys
import os
from typing import Optional
from tqdm import tqdm
import lxml.etree as ET

sys.path.append("..")
from lib.tkb import TheoremKB
from lib.extractors import TrainableExtractor

def register(tkb: TheoremKB, path_pdf: str):
    added_papers = 0

    for dirpath, _, filenames in tqdm(os.walk(path_pdf)):
        for paper_pdf in filenames:
            if not paper_pdf.lower().endswith(".pdf"):
                continue

            base_name = paper_pdf[:-4]
            pdf_dir = os.path.abspath(dirpath) + "/" + paper_pdf

            tkb.add_paper(base_name, pdf_dir)
            added_papers += 1

    tkb.save()
    print("Added",added_papers,"papers!")

def remove(tkb: TheoremKB, name: str):
    tkb.delete_paper(name)
    tkb.save()
    print("removed "+name)

def train(tkb: TheoremKB, extractor_id: str):
    extractor=tkb.extractors[extractor_id]
    class_id=extractor.class_id
    annotated_papers = filter(lambda x: x[1] is not None, 
                        map(lambda paper: (paper, paper.get_training_layer(class_id)), tkb.list_papers()))

    if isinstance(extractor, TrainableExtractor):
        extractor.train(list(annotated_papers), verbose=True)
    else:
        raise Exception("Not trainable.") 
    

def test(tkb: TheoremKB, extractor_id: str, paper_id: str):
    extractor=tkb.extractors[extractor_id]
    paper=tkb.get_paper(paper_id)

    annotated=extractor.apply(paper)
    annotated.reduce()
    annotated.save("test.json")

def info(tkb: TheoremKB, extractor_id: str):
    extractor=tkb.extractors[extractor_id]
    extractor.info()

def summary():
    tkb = TheoremKB()

    print("# Layer: ")
    for class_ in tkb.classes.values():
        print("> ", class_.name,": ", ",".join(class_.labels), sep="")

    print("# Extractors:")
    for extra in tkb.extractors.keys():
        print("> ", extra, sep="")
    print("# Papers:", len(tkb.papers))


if __name__ == "__main__":
    if len(sys.argv) <= 2:
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
    
