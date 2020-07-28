import sys
import os
from typing import Optional
from tqdm import tqdm
import lxml.etree as ET

sys.path.append("..")
from lib.tkb import TheoremKB


def register(tkb: TheoremKB, path_pdf: str, path_src: Optional[str]):

    for paper_pdf in tqdm(os.listdir(path_pdf)):
        if not paper_pdf.lower().endswith(".pdf"):
            continue
        base_name = paper_pdf[:-4]
        pdf_dir = os.path.abspath(path_pdf) + "/" + paper_pdf
        if path_src is None:
            src_dir = None
            has_src = False
        else:
            src_dir = os.path.abspath(path_src) + "/" + base_name
            has_src = os.path.exists(src_dir)
        tkb.add_paper(base_name, pdf_dir, src_dir if has_src else None)

    tkb.save()


def train(tkb: TheoremKB, kind: str):
    annotated_papers = filter(lambda x: x[1] is not None, 
                        map(lambda paper: (paper, paper.get_training_layer(kind)), tkb.list_papers()))

    layer=tkb.layers[kind]
    layer.train(annotated_papers)

def test(tkb: TheoremKB, layer_id: str, paper_id: str):
    paper=tkb.get_paper(paper_id)
    layer=tkb.layers[layer_id]

    annotated=layer.apply(paper)
    annotated.reduce()
    annotated.save("test.json")
    # print(annotated)

def usage():
    pass

if __name__ == "__main__":
    if len(sys.argv) <= 2:
        usage()
        exit(1)

    if sys.argv[1] == "register" and len(sys.argv) > 2:
        path_pdf=sys.argv[2]

        try:
            path_src=sys.argv[3]
        except:
            path_src=None

        tkb=TheoremKB()

        register(tkb, path_pdf, path_src)

    elif sys.argv[1] == "train" and len(sys.argv) > 2:
        layer=sys.argv[2]

        tkb=TheoremKB()

        train(tkb, layer)
    elif sys.argv[1] == "test" and len(sys.argv) > 3:
        layer=sys.argv[2]
        paper=sys.argv[3]

        tkb=TheoremKB()

        test(tkb, layer, paper)
