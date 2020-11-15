"""## TheoremKB management class

Entrypoint functions and registering of annotation classes and extractors.
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from .config import config
from .misc.namespaces import *
from .classes import ALL_CLASSES, AnnotationClass
from .paper import Paper, AnnotationLayerInfo, AnnotationLayerTag, Base
from .extractors import Extractor
from .extractors.misc.features import FeatureExtractor
from .extractors.misc.aggreement import AgreementExtractor
from .extractors.crf import CRFExtractor
from .extractors.results import ResultsLatexExtractor, ResultsNaiveExtractor


class TheoremKB:
    """TheoremKB main class. It's the interface between the database (SQLAlchemy) and the abstractions.
    To use it, you will mostly need a `Session`.

    Example:
    ```
    from sqlalchemy.orm import sessionmaker,scoped_session  # DB
    from lib.tkb import TheoremKB                           # TKB
    from lib.config import config                           # SQL DB location

    session_factory = sessionmaker(bind=config.SQL_ENGINE)  #
    Session = scoped_session(session_factory)               #
    session = Session()                                     # build session

    tkb = TheoremKB()                                # create TKB instance
    tkb.add_paper(session, ...)                      # create paper
    paper = tkb.get_paper(session, ...)              # get paper
    ann_meta = paper.add_annotation_layer("results") # create annotation layer of results class
    ann = paper.get_annotation_layer(ann_meta.id)    # obtain layer instance
    ann.add_box(...)
    ann.save()                # save `ann` changes to file.
    session.commit()          # save `paper` and `ann_meta` creation to DB.
    ``` 
    """

    prefix: str
    """Where the data is stored."""
    classes: Dict[str, AnnotationClass]
    """Annotation classes."""
    extractors: Dict[str, Extractor]
    """Annotation extractors."""

    def __init__(self) -> None:
        self.prefix = config.DATA_PATH

        self.classes = {}
        for l in ALL_CLASSES:
            self.classes[l.name] = l

        extractors = []

        extractors.append(FeatureExtractor("TextLine"))
        extractors.append(FeatureExtractor("String"))
        extractors.append(FeatureExtractor("TextBlock"))
        extractors.append(AgreementExtractor())
        extractors.append(ResultsLatexExtractor())
        extractors.append(ResultsNaiveExtractor())

        for l in ALL_CLASSES:
            if len(l.labels) == 0:
                continue

            extractors.append(
                CRFExtractor(
                    self.prefix, name="line", class_=l, target=f"{ALTO}TextLine"
                )
            )
            extractors.append(
                CRFExtractor(self.prefix, name="str", class_=l, target=f"{ALTO}String")
            )

            if config.ENABLE_TENSORFLOW:
                from .extractors.cnn import CNNExtractor
                from .extractors.cnn1d import CNN1DExtractor

                extractors.append(CNNExtractor(self.prefix, name="", class_=l))
                extractors.append(CNN1DExtractor(self.prefix, name="", class_=l))

        self.extractors = {}
        for e in extractors:
            self.extractors[f"{e.class_.name}.{e.name}"] = e

        Base.metadata.create_all(config.SQL_ENGINE)

    def get_paper(self, session: Session, id: str) -> Optional[Paper]:
        """Get paper class instance for requested ID."""
        return session.query(Paper).get(id)

    def get_layer(self, session: Session, id: str) -> Optional[AnnotationLayerInfo]:
        """Get layer metadata instance given ID."""
        return session.query(AnnotationLayerInfo).get(id)

    def list_papers(
        self,
        session: Session,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        search: Optional[List[Tuple[str, str]]] = None,
        order_by_asc: Optional[Tuple[str, bool]] = None,
        count: bool = False,
    ) -> List[Paper]:
        """Paper query."""
        req = session.query(Paper)

        valid_ann_layers = []

        if search is not None:
            for field, value in search:
                if field == "Paper.title":
                    req = req.filter(Paper.title.ilike(f"%%{value}%%"))
                elif field.startswith("Paper.layers.tag"):
                    valid_ann_layers.append(value)

        if len(valid_ann_layers) > 0:
            valid_tags = (
                session.query(AnnotationLayerTag)
                .filter(AnnotationLayerTag.id.in_(valid_ann_layers))
                .subquery()
            )

            valid_layers = (
                session.query(AnnotationLayerInfo)
                .join(valid_tags, AnnotationLayerInfo.tags)
                .subquery()
            )

            req = req.join(valid_layers)

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

    def list_layer_tags(self, session: Session) -> List[AnnotationLayerTag]:
        """List annotation layer tags."""
        return session.query(AnnotationLayerTag).all()

    def count_layer_tags(
        self, session: Session
    ) -> Dict[str, Tuple[AnnotationLayerTag, Dict[str, int]]]:
        """List annotation layer tags and count layers that have them."""

        tags_with_counts = (
            session.query(AnnotationLayerTag, AnnotationLayerInfo.class_, func.count())
            .join(AnnotationLayerTag, AnnotationLayerInfo.tags)
            .group_by(AnnotationLayerInfo.class_, AnnotationLayerTag.id)
        )

        res = {t.id: (t, {}) for t in session.query(AnnotationLayerTag).all()}

        for (tag, class_, count) in tags_with_counts:
            res[tag.id][1][class_] = count

        return res

    def get_layer_tag(self, session: Session, tag_id: str):
        """Retrieve given layer tag."""
        return session.query(AnnotationLayerTag).get(tag_id)

    def add_layer_tag(
        self,
        session: Session,
        id: str,
        name: str,
        readonly: bool,
        data: dict,
    ):
        """Create new layer tag."""
        new_tag = AnnotationLayerTag(
            id=id,
            name=name,
            readonly=readonly,
            data_str=json.dumps(data),
        )

        session.add(new_tag)

        return new_tag

    def add_paper(self, session: Session, id: str, pdf_path: str) -> Paper:
        """Create new paper."""
        paper = Paper(id=id, pdf_path=pdf_path)
        session.add(paper)
        return paper

    def delete_paper(self, session: Session, id: str):
        """Delete paper from database."""
        paper = session.query(Paper).get(id)
        session.delete(paper)
