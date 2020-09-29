from typing import Tuple
import pytest


import lib.glob as glob 
glob.TEST_INSTANCE = True

from lib.annotations import AnnotationLayer
from lib.classes import HeaderAnnotationClass, SegmentationAnnotationClass
from lib.misc.bounding_box import LabelledBBX, BBX

from lib.paper import Paper
from lib.misc.namespaces import ALTO
from test_tkb import tkb

from sqlalchemy.orm.session import Session
from lib.tkb import TheoremKB


@pytest.fixture
def paper(tkb: Tuple[TheoremKB, Session]):
    tkb, session = tkb
    return tkb.get_paper(session, "0")

@pytest.fixture
def paper_session(tkb: Tuple[TheoremKB, Session]):
    tkb, session = tkb
    return tkb.get_paper(session, "0"), session


def test_get_xml(paper: Paper):
    paper.get_xml()
    xml = paper.get_xml().getroot()  # proc cache

    assert xml.tag == f"{ALTO}alto"
    assert len(xml.findall(f".//{ALTO}Page")) == 1
    assert len(xml.findall(f".//{ALTO}TextBlock")) == 1
    assert len(xml.findall(f".//{ALTO}TextLine")) == 1
    assert len(xml.findall(f".//{ALTO}String")) == 3


def test_get_features(paper: Paper):

    assert len(paper.get_features(f"{ALTO}TextLine", standardize=False, add_context=False)) == 1
    assert len(paper.get_features(f"{ALTO}String")) == 3

    try:
        paper.get_features("unknown..")
        assert False
    except Exception as e:
        pass


def test_apply_layer_and_get_title(paper: Paper):

    test_ann = AnnotationLayer()
    test_ann.add_box(LabelledBBX("title", 0, 1, 55, 65, 120, 90))

    applied_layer = paper.apply_annotations_on(test_ann, f"{ALTO}String")
    paper.add_annotation_layer("header", applied_layer)
    paper._refresh_title()
    assert paper.title == "Dummy"


def test_box_validator(paper_session: Tuple[Paper, Session]):
    paper, session = paper_session

    segm_ann = AnnotationLayer()
    segm_ann.add_box(LabelledBBX("front", 0, 1, 55, 65, 120, 90))
    paper.add_annotation_layer("segmentation", segm_ann)

    session.commit()

    box_val = paper.get_box_validator(SegmentationAnnotationClass())
    for box, gt in zip(paper.get_xml().getroot().findall(f".//{ALTO}String"), [True, True, True]):
        assert gt == box_val(BBX.from_element(box))

    box_val = paper.get_box_validator(HeaderAnnotationClass())
    for box, gt in zip(paper.get_xml().getroot().findall(f".//{ALTO}String"), [True, False, False]):
        assert gt == box_val(BBX.from_element(box))

def test_render_pdf(paper: Paper):
    rdr = paper.render()
    assert len(rdr) == 1
    rdr = rdr[0]
    assert rdr[0].shape == (842, 595, 3) # height width depth
    assert paper.get_render_scales() == [1.0]
    assert 0.6 < paper.get_render_scales(512, 512)[0] < 0.61

    rdr2 = paper.render(512, 512)
    img = rdr2[0][0]
    assert img.shape[0] <= 512 and img.shape[1] <= 512


def test_json_serializer(paper: Paper):
    json = paper.to_web(["header", "segmentation"])

    assert json == {
        "id": "0",
        "pdf": f"/papers/0/pdf",
        "classStatus": {
            "header": {
                "count": 0
            },
            "segmentation": {
                "count": 1
            }
        },
        "title": "Dummy"
    }