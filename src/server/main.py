import falcon
from falcon import Request, Response
import json
import sys, os
import shortuuid
sys.path.append("..")

from lib.paper import AnnotationLayerInfo
from lib.tkb import Layer, TheoremKB
from lib.misc.bounding_box import LabelledBBX

class LayersResource(object):
    tkb: TheoremKB

    def __init__(self, tkb: TheoremKB) -> None:
        self.tkb = tkb

    def get_entry(self, layer: Layer):
        return {
            "id": layer.name,
            "schema": layer.schema
        }

    def on_get(self, req, resp, layer_id):
        print("??")
        if layer_id == "":
            resp.media = [self.get_entry(layer) for layer in self.tkb.layers.values()]
        else:
            resp.media = self.get_entry(self.tkb.layers[layer_id])



class PaperResource(object):
    tkb: TheoremKB

    def __init__(self, tkb: TheoremKB) -> None:
        self.tkb = tkb

    def on_get(self, req, resp, paper_id):

        if paper_id == "":
            resp.media = [p.to_web(self.tkb.layers.keys()) for p in self.tkb.list_papers()]
        else:
            try:
                resp.media = self.tkb.get_paper(paper_id).to_web(self.tkb.layers.keys())
            except Exception as ex:
                resp.media = {"error": str(ex)}
                resp.status = "404 Not Found"

class PaperPDFResource(object):
    tkb: TheoremKB

    def __init__(self, tkb: TheoremKB) -> None:
        self.tkb = tkb

    def on_get(self, req: Request, resp: Response, *, paper_id: str):
        paper = self.tkb.get_paper(paper_id)
        try:
            pdf = open(paper.pdf_path, "rb")
            resp.stream = pdf
            resp.content_length = os.path.getsize(paper.pdf_path)
            resp.content_type = "application/pdf"
        except Exception as e:
            resp.media = str(e)
            resp.status = "400"


class PaperLayerResource(object):
    def __init__(self, tkb: TheoremKB) -> None:
        self.tkb = tkb

    def on_get(self, req, resp, *, paper_id: str, layer: str):
        layers = self.tkb.get_paper(paper_id).layers
        
        if layer == "":
            resp.media = [v.to_web(paper_id) for v in layers.values()]
        elif layer in layers:
            resp.media = layers[layer].to_web(paper_id)
        else:
            print(layers)

    def on_post(self, req: Request, resp: Response, *, paper_id: str, layer: str):

        if layer != "":
            resp.status = "405 Method Not Allowed"
            return

        paper = self.tkb.get_paper(paper_id)
        params = json.load(req.stream)

        new_id = shortuuid.uuid()
        new_layer = AnnotationLayerInfo(new_id, params["name"], params["kind"], params["training"])
        paper.add_annotation_layer(new_layer)
        tkb.save()
        resp.media = new_layer.to_web(paper_id)
    #def on_patch(self, req: Request, resp: Response, *, paper_id: str, layer: str):
    #    paper = self.tkb.get_paper(paper_id)
    #    params = json.load(req.stream)
    #    print(params)
#
    #    if "status" in params and params['status'] in [x.value for x in AnnotationStatus.#__members__.values()]:
    #        paper.annotation_status[layer] = AnnotationStatus(params['status'])
    #        tkb.save()
    #        print("ok.")
    #        resp.media  = {"id": layer, "paperId": paper_id, "status": params['status']}
    #    else:
    #        resp.status = "400"
    #        resp.media  = {"error": "TODO."}
    #        

class BoundingBoxResource(object):
    tkb: TheoremKB
    
    def __init__(self, tkb: TheoremKB) -> None:
        self.tkb = tkb

    def on_get(self, req: Request, resp: Response, *, paper_id: str, layer: str, bbx: str):
        paper = self.tkb.get_paper(paper_id)
        annot = paper.get_annotation_layer(layer)
        boxes = annot.get_boxes()
        if bbx == "":
            resp.media = [box.to_web(id, paper_id, layer) for id,box in boxes.items()]
        else:
            resp.media = boxes[bbx].to_web(bbx, paper_id, layer)
    
    def on_post(self, req: Request, resp: Response, *, paper_id: str, layer: str, bbx: str):
        paper = self.tkb.get_paper(paper_id)
        annot = paper.get_annotation_layer(layer)

        print("loaded layer")
        if bbx != "":
            resp.status = "405 Method Not Allowed"
            return
        params = json.load(req.stream)
        try:
            page = int(params["page_num"])
            min_h = float(params["min_h"])
            min_v = float(params["min_v"])
            max_h = float(params["max_h"])
            max_v = float(params["max_v"])
            label = params["label"]
        except (KeyError, ValueError):
            resp.status = "400 Bad Request"
            return


        print("parsed params.")
        box = LabelledBBX(label, 0, page, min_h, min_v, max_h, max_v)
        id = annot.add_box(box)
        annot.save()
        resp.media = box.to_web(id, paper_id, layer)
        
    def on_delete(self, req: Request, resp: Response, *, paper_id: str, layer: str, bbx: str):
        assert bbx != ""

        paper = self.tkb.get_paper(paper_id)
        annot = paper.get_annotation_layer(layer)
        annot.delete_box(bbx)
        annot.save()

        resp.media = {"message": "success"}

        
    def on_put(self, req: Request, resp: Response, *, paper_id: str, layer: str, bbx: str):
        assert bbx != ""
        paper = self.tkb.get_paper(paper_id)
        annot = paper.get_annotation_layer(layer)

        params = json.load(req.stream)

        page = params["page_num"]
        min_h = params["min_h"]
        min_v = params["min_v"]
        max_h = params["max_h"]
        max_v = params["max_v"]
        label = params["label"]

        box = LabelledBBX(label, 0, page, min_h, min_v, max_h, max_v)
        annot.move_box(bbx, box)
        annot.save()

        resp.media = box.to_web(bbx, paper_id, layer)



class CORSComponent(object):
    def process_response(self, req, resp, resource, req_succeeded):
        resp.set_header('Access-Control-Allow-Origin', '*')

        if (req_succeeded
            and req.method == 'OPTIONS'
            and req.get_header('Access-Control-Request-Method')
            ):
            # NOTE(kgriffs): This is a CORS preflight request. Patch the
            #   response accordingly.

            allow = resp.get_header('Allow')
            resp.delete_header('Allow')

            allow_headers = req.get_header(
                'Access-Control-Request-Headers',
                default='*'
            )

            resp.set_headers((
                ('Access-Control-Allow-Methods', allow),
                ('Access-Control-Allow-Headers', allow_headers),
                ('Access-Control-Max-Age', '86400'),  # 24 hours
            ))


api = falcon.API(middleware=[CORSComponent()])
api.req_options.auto_parse_form_urlencoded = True
tkb = TheoremKB()

api.add_route('/layers/{layer_id}', LayersResource(tkb))
api.add_route('/papers/{paper_id}', PaperResource(tkb))
api.add_route('/papers/{paper_id}/pdf', PaperPDFResource(tkb))
api.add_route('/papers/{paper_id}/layers/{layer}', PaperLayerResource(tkb))
api.add_route('/papers/{paper_id}/layers/{layer}/bbx/{bbx}', BoundingBoxResource(tkb))
