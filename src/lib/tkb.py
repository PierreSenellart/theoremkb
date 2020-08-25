from __future__ import annotations
from typing import Dict, List, Optional
import jsonpickle

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import sessionmaker, Session

from .config import DATA_PATH, SQL_ENGINE
from .classes import ALL_CLASSES, AnnotationClass
from .paper import Paper, AnnotationLayerInfo
from .extractors import Extractor
from .extractors.crf import CRFFeatureExtractor
from .extractors.segmentation import SegmentationCRFExtractor, SegmentationStringCRFExtractor
from .extractors.header import HeaderCRFExtractor
from .extractors.results import ResultsLatexExtractor, ResultsCRFExtractor, ResultsStringCRFExtractor


class TheoremKB:

    prefix: str
    classes: Dict[str, AnnotationClass]
    extractors: Dict[str, Extractor]

    def __init__(self, prefix=DATA_PATH) -> None:
        self.prefix = prefix

        self.classes = {}
        for l in ALL_CLASSES:
            self.classes[l.name] = l

        self.extractors = {}
        crf = SegmentationCRFExtractor(prefix)
        crfstr = SegmentationStringCRFExtractor(prefix)

        res_crf = ResultsCRFExtractor(prefix)
        resstr_crf = ResultsStringCRFExtractor(prefix)

        hd = HeaderCRFExtractor(prefix)
        crf_ft = CRFFeatureExtractor(crf)
        for e in [crf, crfstr, crf_ft, hd, ResultsLatexExtractor(), res_crf, resstr_crf]:
            self.extractors[f"{e.class_.name}.{e.name}"] = e

    def get_paper(self, session: Session, id: str) -> Paper:
        try:
            return session.query(Paper).get(id)
        except Exception as e:
            raise Exception("PaperNotFound")

    def get_layer(self, session: Session, id: str) -> AnnotationLayerInfo:
        try:
            return session.query(AnnotationLayerInfo).get(id)
        except Exception as e:
            raise Exception("LayerNotFound")

    def list_papers(self, session: Session) -> List[Paper]:
        return session.query(Paper).all()

    def add_paper(self, session: Session, id: str, pdf_path: str):
        session.add(Paper(id=id, pdf_path=pdf_path))

    def delete_paper(self, session: Session, id: str):
        paper = session.query(Paper).get(id)
        session.delete(paper)
