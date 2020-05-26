import re, sys, fitz
from bounding_box import BBX

from PIL import Image               # to load images
from IPython.display import display # to display image


ALTO = "{http://www.loc.gov/standards/alto/ns-v3#}"

class ResultsBoundingBoxes:
    """
    Result bounding boxes container.
    """

    def __init__(self, xml_annot):
        """
        Parse an XML annotation file to gather theorems bounding boxes.
        """
        self._data        = {}
        self.LENGTH_LIMIT = 50 # Ignore results that could have captured the whole document.

        extraction_re = re.compile(r"uri:theorem\.(Theorem|Lemma|Proposition|Definition)\.([0-9]+)")
        

        for annotation in xml_annot.findall(".//ANNOTATION/ACTION[@type='uri']/.."):
            dest = annotation.find("ACTION/DEST")
            link_theorem_match = extraction_re.search(dest.text)
            if link_theorem_match is None:
                continue

            kind    = link_theorem_match.group(1)
            if kind not in self._data:
                self._data[kind] = {}

            index   = int(link_theorem_match.group(2))

            if index not in self._data[kind]:
                self._data[kind][index] = []

            page_num = annotation.get("pagenum")

            quadpoints = annotation.findall("QUADPOINTS/QUADRILATERAL/POINT")
            min_h, min_v, max_h, max_v = None, None, None, None
            for point in quadpoints:
                h, v = float(point.get("HPOS")), float(point.get("VPOS"))

                if min_h is None:
                    min_h, max_h = h, h
                    min_v, max_v = v, v
                else:
                    min_h = min(min_h, h)
                    max_h = max(max_h, h)
                    min_v = min(min_v, v)
                    max_v = max(max_v, v)
            
            self._data[kind][index].append(BBX(page_num, min_h, min_v, max_h, max_v))

    def get_kind(self, node, mode="full"):
        """
        Get the type of a node, containing HPOS, VPOS, HEIGHT, WIDTH fields.
        Mode can be either 'intersect' or 'full'.
        Returns Theorem|Lemma|Proposition|Definition|Text
        """
        min_h, min_v = float(node.get("HPOS")), float(node.get("VPOS"))
        max_h, max_v = min_h + float(node.get("WIDTH")), min_v + float(node.get("HEIGHT"))


        while node.tag != f"{ALTO}Page":
            node = node.getparent()
        page_num     = node.get("PHYSICAL_IMG_NR")
        
        box = BBX(page_num, min_h, min_v, max_h, max_v)

        for (kind, results) in self._data.items():
            for result_id, bbxes in results.items():
                if len(bbxes) <= self.LENGTH_LIMIT:
                    for bbx in bbxes:
                        if mode == "intersect":
                            if bbx.intersects(box):
                                return kind, result_id
                        elif mode == "full":
                            if bbx.contains(box):
                                return kind, result_id
                        else:
                            print(f"Error: unknown mode '{mode}'", file=sys.stderr)
                            exit(1)

        return "Text", 0


    def render(self, id, pdf):

        for data in self._data.values():
            if id in data:
                render_result(data[id], pdf)
                return
        print("Not found.")
        

    def __len__(self):
        return sum(len(x) for x in self._data.values())


def render_box(bounding_box, pdf):
    page= pdf.loadPage(int(bounding_box.page_num)-1)
    bb  = fitz.Rect(bounding_box.min_h, bounding_box.min_v, bounding_box.max_h, bounding_box.max_v)
    pix = page.getPixmap(clip=bb)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    img.show()
    
def render_result(bounding_boxes, pdf, context=20):
    bbxs = BBX.from_list(bounding_boxes)
    for bbx in bbxs:
        render_box(bbx.extend(50), pdf)
