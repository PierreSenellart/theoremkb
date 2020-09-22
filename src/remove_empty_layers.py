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

if len(sys.argv) == 2:
    name = sys.argv[1]

    count = 0
    tkb=TheoremKB()
    session=Session()
    for paper in tqdm(tkb.list_papers(session)):
        for layer in list(filter(lambda l: l.name == name, paper.layers)):
            annotations = paper.get_annotation_layer(layer.id)
            if len(annotations.bbxs) == 0:
                raise NotImplementedError
                paper.remove_annotation_layer(layer.id)
                count += 1
    session.commit()
    print("Removed "+str(count)+" layers.")


print("ok.")
Session.remove()