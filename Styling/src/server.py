"""
TKB Server - REST API
"""
from __future__ import absolute_import

import json, os, falcon, shortuuid
from falcon import Request, Response
from sqlalchemy.orm import Session

from lib.extractors import Extractor, TrainableExtractor
from lib.paper import AnnotationLayerTag, ParentModelNotFoundException
from lib.tkb import AnnotationClass, TheoremKB
from lib.misc.bounding_box import LabelledBBX
from lib.config import config

SQL_ENGINE = config.SQL_ENGINE

class AnnotationClassResource(object):
    tkb: TheoremKB

    def __init__(self, tkb_: TheoremKB) -> None:
        self.tkb = tkb_

    def get_entry(self, class_: AnnotationClass):
        return {
            "id": class_.name,
            "labels": class_.labels,
            "parents": [x.to_web() for x in class_.parents],
        }

    def on_get(self, _, resp, class_id):
        if class_id == "":
            resp.media = [self.get_entry(layer) for layer in self.tkb.classes.values()]
        else:
            resp.media = self.get_entry(self.tkb.classes[class_id])


class AnnotationClassExtractorResource(object):
    tkb: TheoremKB

    def __init__(self, tkb_: TheoremKB):
        self.tkb = tkb_

    def get_entry(self, extractor: Extractor):
        res = {
            "id": extractor.name,
            "classId": extractor.class_.name,
            "description": extractor.description,
            "classParameters": extractor.class_parameters,
        }

        if isinstance(extractor, TrainableExtractor):
            res["trainable"] = True
            res["trained"] = extractor.is_trained or False
        else:
            res["trained"] = False

        return res

    def on_get(self, _, resp, class_id, extractor_id):
        if extractor_id == "":
            resp.media = [
                self.get_entry(e) for e in self.tkb.extractors.values() if e.class_.name == class_id
            ]
        else:
            resp.media = self.get_entry(self.tkb.extractors[f"{class_id}.{extractor_id}"])


class PaperResource(object):
    tkb: TheoremKB

    def __init__(self, tkb_: TheoremKB):
        self.tkb = tkb_

    def on_get(self, req, resp, paper_id):
        session = Session(bind=SQL_ENGINE)

        if paper_id == "":
            try:
                params = json.loads(req.params["q"])
            except (json.JSONDecodeError, KeyError):
                params = {}

            order_by = params.get("order_by", None)
            search = params.get("search", [])
            offset = int(params.get("offset", 0))
            limit = int(params.get("limit", 10))

            count = self.tkb.list_papers(session, search=search, count=True)
            req = self.tkb.list_papers(session, offset, limit, search, order_by)
            papers = [p.to_web(list(self.tkb.classes.keys())) for p in req]

            resp.media = {
                "count": count,
                "papers": papers,
            }
        else:
            try:
                resp.media = self.tkb.get_paper(session, paper_id).to_web(
                    list(self.tkb.classes.keys())
                )
            except KeyError as ex:
                resp.media = {"error": str(ex)}
                resp.status = "404 Not Found"
        session.commit()
        session.close()


class LayerTagResource(object):
    tkb: TheoremKB

    def __init__(self, tkb_: TheoremKB):
        self.tkb = tkb_

    def on_get(self, req, resp, *, tag_id, paper_id=None, layer_id=None):
        session = Session(bind=SQL_ENGINE)

        if tag_id == "":
            if paper_id is None or layer_id is None:  # /tags/.. route
                addCounts = req.params.get("addCounts", False)

                if addCounts:
                    lst = [
                        tag.to_web(counts)
                        for (tag, counts) in tkb.count_layer_tags(session).values()
                    ]
                else:
                    lst = [tag.to_web() for tag in tkb.list_layer_tags(session)]
                resp.media = lst
            else:  # /papers/../layers/../tags/.. route
                layer = tkb.get_layer(session, layer_id)
                assert layer.paper_id == paper_id
                resp.media = [tag.to_web() for tag in layer.tags]

        else:
            try:
                resp.media = self.tkb.get_layer_tag(session, tag_id).to_web()
            except KeyError as ex:
                resp.media = {"error": str(ex)}
                resp.status = "404 Not Found"

        session.close()

    def on_post(self, req: Request, resp: Response, *, tag_id: str, paper_id=None, layer_id=None):
        session = Session(bind=SQL_ENGINE)

        if paper_id is None or layer_id is None:  # /tags/.. route
            params = json.load(req.stream)

            if not "name" in params:
                resp.status = "400 Bad request"

            name = params["name"]
            id = shortuuid.uuid()

            resp.media = self.tkb.add_layer_tag(session, id, name, False, {"from": "user"}).to_web()
        else:
            pass

        session.commit()
        session.close()

    def on_put(self, _req: Request, resp: Response, *, tag_id: str, paper_id=None, layer_id=None):

        session = Session(bind=SQL_ENGINE)

        if paper_id is None or layer_id is None:  # /tags/.. route
            pass
        else:
            layer = tkb.get_layer(session, layer_id)
            assert layer.paper_id == paper_id
            tag = tkb.get_layer_tag(session, tag_id)

            layer.tags.append(tag)

            resp.media = tag.to_web()

        session.commit()
        session.close()

    def on_patch(self, req: Request, resp: Response, *, tag_id: str, paper_id=None, layer_id=None):
        session = Session(bind=SQL_ENGINE)
        layer_tag = self.tkb.get_layer_tag(session, tag_id)
        params = json.load(req.stream)

        resp.media = {"id": tag_id}

        if "name" in params:
            layer_tag.name = params["name"]
            resp.media["name"] = params["name"]

        session.commit()
        session.close()

    def on_delete(self, req: Request, resp: Response, *, tag_id: str, paper_id=None, layer_id=None):
        session = Session(bind=SQL_ENGINE)

        if paper_id is None or layer_id is None:  # /tags/.. route
            session.query(AnnotationLayerTag).filter(AnnotationLayerTag.id == tag_id).delete()
            resp.media = {"message": "success"}
        else:
            layer = tkb.get_layer(session, layer_id)
            assert layer.paper_id == paper_id
            tag = tkb.get_layer_tag(session, tag_id)
            layer.tags.remove(tag)
            resp.media = {"message": "success"}

        session.commit()
        session.close()


class PaperPDFResource(object):
    tkb: TheoremKB

    def __init__(self, tkb_: TheoremKB) -> None:
        self.tkb = tkb_

    def on_get(self, _req: Request, resp: Response, *, paper_id: str):
        session = Session(bind=SQL_ENGINE)
        paper = self.tkb.get_paper(session, paper_id)
        session.close()
        try:
            pdf = open(paper.pdf_path, "rb")
            resp.stream = pdf
            resp.content_length = os.path.getsize(paper.pdf_path)
            resp.content_type = "application/pdf"
        except Exception as e:
            resp.media = str(e)
            resp.status = "400"


class PaperAnnotationLayerResource(object):
    tkb: TheoremKB

    def __init__(self, tkb: TheoremKB) -> None:
        self.tkb = tkb

    def on_get(self, req, resp, *, paper_id: str, layer_id: str):
        session = Session(bind=SQL_ENGINE)

        if layer_id == "":
            layers = self.tkb.get_paper(session, paper_id).layers
            resp.media = [v.to_web() for v in layers]
        else:
            resp.media = self.tkb.get_layer(session, layer_id).to_web()
        session.close()

    def on_post(self, req: Request, resp: Response, *, paper_id: str, layer_id: str):

        if layer_id != "":
            resp.status = falcon.HTTP_BAD_REQUEST
            return

        try:
            session = Session(bind=SQL_ENGINE)
            paper = self.tkb.get_paper(session, paper_id)
            params = json.load(req.stream)

            if "extractor" in params:
                extractor_name = params["extractor"]
                extractor_id = params["class"] + "." + extractor_name
                extractor = self.tkb.extractors[extractor_id]
                new_layer = extractor.apply_and_save(paper, params.get("reqs", []))

                if params["class"] == "header":
                    paper.title = "__undef__"
            else:
                new_layer = paper.add_annotation_layer(params["class"])

            session.commit()

            resp.media = new_layer.to_web()

            session.close()

        except ParentModelNotFoundException as e:
            resp.status = falcon.HTTP_BAD_REQUEST
            resp.media = {"message": str(e)}

    def on_delete(self, req: Request, resp: Response, *, paper_id: str, layer_id: str):
        session = Session(bind=SQL_ENGINE)
        paper = self.tkb.get_paper(session, paper_id)

        # refresh title.
        info = paper.get_annotation_info(layer_id)
        if info.class_ == "header":
            paper.title = "__undef__"

        paper.remove_annotation_layer(session, layer_id)

        resp.media = {"message": "success"}

        session.commit()
        session.close()


class BoundingBoxResource(object):
    tkb: TheoremKB

    def __init__(self, tkb: TheoremKB) -> None:
        self.tkb = tkb

    def on_get(self, req: Request, resp: Response, *, paper_id: str, layer_id: str, bbx_id: str):
        session = Session(bind=SQL_ENGINE)
        paper = self.tkb.get_paper(session, paper_id)
        session.close()
        annot = paper.get_annotation_layer(layer_id)
        boxes = annot.get_boxes()
        if bbx_id == "":
            resp.media = [box.to_web(id, paper_id, layer_id) for id, box in boxes.items()]
        else:
            resp.media = boxes[bbx_id].to_web(bbx_id, paper_id, layer_id)

    def on_post(self, req: Request, resp: Response, *, paper_id: str, layer_id: str, bbx_id: str):
        session = Session(bind=SQL_ENGINE)
        paper = self.tkb.get_paper(session, paper_id)
        annot = paper.get_annotation_layer(layer_id)

        print("loaded layer")
        if bbx_id != "":
            resp.status = "405 Method Not Allowed"
            return
        params = json.load(req.stream)
        try:
            page = int(params["pageNum"])
            min_h = float(params["minH"])
            min_v = float(params["minV"])
            max_h = float(params["maxH"])
            max_v = float(params["maxV"])
            label = params["label"]
        except (KeyError, ValueError):
            resp.status = "400 Bad Request"
            return

        print("parsed params.")
        box = LabelledBBX(label, 0, page, min_h, min_v, max_h, max_v)
        id = annot.add_box(box)
        annot.save()
        resp.media = box.to_web(id, paper_id, layer_id)

        # refresh title.
        info = paper.get_annotation_info(layer_id)
        if info.class_ == "header":
            paper.title = "__undef__"

        session.commit()
        session.close()

    def on_delete(self, req: Request, resp: Response, *, paper_id: str, layer_id: str, bbx_id: str):
        assert bbx_id != ""

        session = Session(bind=SQL_ENGINE)
        paper = self.tkb.get_paper(session, paper_id)
        annot = paper.get_annotation_layer(layer_id)

        annot.delete_box(bbx_id)
        annot.save()

        resp.media = {"message": "success"}

        # refresh title.
        info = paper.get_annotation_info(layer_id)
        if info.class_ == "header":
            paper.title = "__undef__"

        session.commit()
        session.close()

    def on_put(self, req: Request, resp: Response, *, paper_id: str, layer_id: str, bbx_id: str):
        assert bbx_id != ""
        session = Session(bind=SQL_ENGINE)
        paper = self.tkb.get_paper(session, paper_id)
        annot = paper.get_annotation_layer(layer_id)

        params = json.load(req.stream)

        page = params["pageNum"]
        min_h = params["minH"]
        min_v = params["minV"]
        max_h = params["maxH"]
        max_v = params["maxV"]
        label = params["label"]

        box = LabelledBBX(label, 0, page, min_h, min_v, max_h, max_v)
        annot.move_box(bbx_id, box)
        annot.save()

        resp.media = box.to_web(bbx_id, paper_id, layer_id)

        # refresh title.
        info = paper.get_annotation_info(layer_id)
        if info.class_ == "header":
            paper.title = "__undef__"

        session.commit()
        session.close()


api = falcon.API()
api.req_options.auto_parse_form_urlencoded = True
tkb = TheoremKB()

api.add_route("/classes/{class_id}", AnnotationClassResource(tkb))
api.add_route(
    "/classes/{class_id}/extractors/{extractor_id}", AnnotationClassExtractorResource(tkb)
)
api.add_route("/tags/{tag_id}", LayerTagResource(tkb))
api.add_route("/papers/{paper_id}/layers/{layer_id}/tags/{tag_id}", LayerTagResource(tkb))
api.add_route("/papers/{paper_id}", PaperResource(tkb))
api.add_route("/papers/{paper_id}/pdf", PaperPDFResource(tkb))
api.add_route("/papers/{paper_id}/layers/{layer_id}", PaperAnnotationLayerResource(tkb))
api.add_route("/papers/{paper_id}/layers/{layer_id}/bbx/{bbx_id}", BoundingBoxResource(tkb))
