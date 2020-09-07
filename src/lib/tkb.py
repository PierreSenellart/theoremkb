from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import time

from sqlalchemy.orm import Session

from .config import DATA_PATH, SQL_ENGINE, ENABLE_TENSORFLOW
from .misc.namespaces import *
from .classes import ALL_CLASSES, AnnotationClass
from .paper import Paper, AnnotationLayerInfo, AnnotationLayerBatch

from .extractors import Extractor
from .extractors.misc.features import FeatureExtractor
from .extractors.misc.aggreement import AgreementExtractor
from .extractors.crf import CRFExtractor
from .extractors.results import ResultsLatexExtractor

if ENABLE_TENSORFLOW:
    from .extractors.cnn import CNNExtractor


class TheoremKB:

    prefix: str
    classes: Dict[str, AnnotationClass]
    extractors: Dict[str, Extractor]

    def __init__(self, prefix=DATA_PATH) -> None:
        self.prefix = prefix

        self.classes = {}
        for l in ALL_CLASSES:
            self.classes[l.name] = l

        extractors = []

        extractors.append(FeatureExtractor("TextLine"))
        extractors.append(FeatureExtractor("String"))
        extractors.append(FeatureExtractor("TextBlock"))
        extractors.append(AgreementExtractor())
        extractors.append(ResultsLatexExtractor())

        for l in ALL_CLASSES:
            if len(l.labels) == 0:
                continue

            extractors.append(CRFExtractor(prefix, name="line", class_=l, target=f"{ALTO}TextLine"))
            extractors.append(CRFExtractor(prefix, name="str", class_=l, target=f"{ALTO}String"))

            if ENABLE_TENSORFLOW:
                extractors.append(CNNExtractor(prefix, name="", class_=l))

        self.extractors = {}
        for e in extractors:
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

    def list_papers(
        self,
        session: Session,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        search: List[Tuple[str, str]] = [],
        order_by_asc: Optional[Tuple[str, bool]] = None,
        count: bool = False,
    ) -> List[Paper]:
        req = session.query(Paper)

        valid_ann_layers = []

        for field, value in search:
            if field == "Paper.title":
                req = req.filter(Paper.title.ilike(f"%%{value}%%"))
            elif field.startswith("Paper.layers.group"):
                valid_ann_layers.append(value)

        if len(valid_ann_layers) > 0:
            req = req.join(
                session.query(AnnotationLayerInfo)
                .filter(AnnotationLayerInfo.group_id.in_(valid_ann_layers))
                .subquery()
            )

        if order_by_asc is not None:
            order_by, asc = order_by_asc
            prop = None
            if order_by == "Paper.title":
                prop = Paper.title
            elif order_by == "Paper.id":
                prop = Paper.id

            if prop is not None:
                if asc:
                    req = req.order_by(prop.asc())
                else:
                    req = req.order_by(prop.desc())

        if count:
            return req.count()
        else:
            if offset is not None:
                req = req.offset(offset)
            if limit is not None:
                req = req.limit(limit)
            return req.all()

    def list_layer_groups(self, session: Session):
        return session.query(AnnotationLayerBatch).all()

    def get_layer_group(self, session: Session, group_id: str):
        return session.query(AnnotationLayerBatch).get(group_id)

    def add_layer_group(
        self, session: Session, id: str, name: str, class_: str, extractor: str, extractor_info: str
    ):
        session.add(
            AnnotationLayerBatch(
                id=id, name=name, class_=class_, extractor=extractor, extractor_info=extractor_info
            )
        )

    def add_paper(self, session: Session, id: str, pdf_path: str):
        session.add(Paper(id=id, pdf_path=pdf_path))

    def delete_paper(self, session: Session, id: str):
        paper = session.query(Paper).get(id)
        session.delete(paper)
