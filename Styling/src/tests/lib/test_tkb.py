from typing import Tuple
import os
import pytest
from sqlalchemy.orm.session import Session

import lib.glob as glob 
glob.TEST_INSTANCE = True

from lib.tkb import TheoremKB
from lib.config import config

@pytest.fixture()
def tkb(tmpdir):
    config.DATA_PATH = tmpdir
    config.ENABLE_TENSORFLOW = False
    tkb     = TheoremKB()
    session = config.Session()


    paper = tkb.add_paper(session, "0", os.path.join(os.path.dirname(__file__), "../assets/dummy.pdf"))
    paper.title = "Dummy"
    paper2 = tkb.add_paper(session, "1", os.path.join(os.path.dirname(__file__), "../assets/dummy.pdf"))
    paper2.title = "another dummy paper"

    tag   = tkb.add_layer_tag(session, "0", "tag", False, {})

    lyr   = paper.add_annotation_layer("segmentation")
    lyr.tags.append(tag)

    session.commit()

    return tkb, session


def test_tkb_initialization(tmpdir):
    global config
    config.DATA_PATH = tmpdir
    config.ENABLE_TENSORFLOW = True
    tkb     = TheoremKB()
    session = config.Session()

    assert os.path.exists(f"{tmpdir}/tkb.sqlite")
    assert len(tkb.list_layer_tags(session)) == 0
    assert len(tkb.list_papers(session)) == 0 
    
def test_tkb_fixture(tkb):
    tkb, session = tkb
    assert len(tkb.list_papers(session)) == 2
    assert len(tkb.list_layer_tags(session)) == 1
    assert len(tkb.get_layer_tag(session, "0").layers) == 1 
    assert len(tkb.get_paper(session, "0").layers) == 1


def test_delete_paper(tkb: Tuple[TheoremKB, Session]):
    tkb, session = tkb
    tkb.delete_paper(session, "0")
    session.commit()

    assert len(tkb.list_papers(session)) == 1
    assert tkb.get_paper(session, "0") is None
    assert len(tkb.get_layer_tag(session, "0").layers) == 0 
    assert len(tkb.list_layer_tags(session)) == 1

def test_get_unknown_content(tkb: Tuple[TheoremKB, Session]):
    tkb, session = tkb

    assert tkb.get_layer(session, "doesn't exist") is None
    assert tkb.get_layer_tag(session, "doesn't exist") is None
    assert tkb.get_paper(session, "doesn't exist") is None

def test_search_papers(tkb: Tuple[TheoremKB, Session]):
    tkb, session = tkb

    # count
    assert tkb.list_papers(session, count=True) == 2
    # limit
    assert len(tkb.list_papers(session, limit=1)) == 1
    # offset 
    assert tkb.list_papers(session, offset=1)[0].id == "1"
    # order
    assert tkb.list_papers(session, order_by_asc=("Paper.id", False))[0].id == "1"
    assert tkb.list_papers(session, order_by_asc=("Paper.title", True))[0].id == "0"
    # filter tags
    assert len(tkb.list_papers(session, search=[("Paper.layers.tag", "0")])) == 1
    # filter title
    assert len(tkb.list_papers(session, search=[("Paper.title", "another")])) == 1

def test_count_layer_tags(tkb: Tuple[TheoremKB, Session]):
    tkb, session = tkb

    tag_counts = tkb.count_layer_tags(session)

    assert len(tag_counts) == 1
    assert tag_counts["0"][1]["segmentation"] == 1
    assert tag_counts["0"][0].id == "0"
