from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import time

from sqlalchemy.orm import Session


from .config import DATA_PATH, SQL_ENGINE
from .classes import ALL_CLASSES, AnnotationClass
from .paper import Paper, AnnotationLayerInfo, AnnotationLayerBatch
from .extractors import Extractor
from .extractors.misc.features import FeatureExtractor
from .extractors.misc.aggreement import AgreementExtractor
from .extractors.segmentation import (
    SegmentationCRFExtractor,
    SegmentationStringCRFExtractor,
    SegmentationCNNExtractor,
)
from .extractors.header import HeaderCRFExtractor
from .extractors.results import (
    ResultsLatexExtractor,
    ResultsCRFExtractor,
    ResultsStringCRFExtractor,
    ResultsCNNExtractor
)


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
        segcnn = SegmentationCNNExtractor(prefix)

        res_crf = ResultsCRFExtractor(prefix)
        resstr_crf = ResultsStringCRFExtractor(prefix)
        res_cnn = ResultsCNNExtractor(prefix)

        hd = HeaderCRFExtractor(prefix)
        ft = FeatureExtractor("TextLine")
        ft_str = FeatureExtractor("String")
        ft_blk = FeatureExtractor("TextBlock")
        
        for e in [crf, crfstr, ft, ft_str, ft_blk, segcnn, hd, ResultsLatexExtractor(), res_crf, res_cnn, resstr_crf, AgreementExtractor()]:
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
        order_by: Optional[Tuple[str, bool]] = None,
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
            req = req.join(session.query(AnnotationLayerInfo).filter(AnnotationLayerInfo.group_id.in_(valid_ann_layers)).subquery())

        if order_by is not None:
            order_by, asc = order_by
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

    def add_layer_group(self, session: Session, id: str, name: str, class_: str, extractor: str, extractor_info: str):
        session.add(AnnotationLayerBatch(id=id, name=name, class_=class_, extractor=extractor, extractor_info=extractor_info))

    def add_paper(self, session: Session, id: str, pdf_path: str):
        session.add(Paper(id=id, pdf_path=pdf_path))

    def delete_paper(self, session: Session, id: str):
        paper = session.query(Paper).get(id)
        session.delete(paper)
