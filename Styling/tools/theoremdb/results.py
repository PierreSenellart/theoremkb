import re, sys, fitz
from .bounding_box import BBX
from scipy.spatial.kdtree import KDTree

from PIL import Image               # to load images
from IPython.display import display # to display image


ALTO = "{http://www.loc.gov/standards/alto/ns-v3#}"

class ResultsBoundingBoxes:
    """
    Result bounding boxes container.
    """

    def __init__(self, xml_annot,merge_all=True):
        """
        Parse an XML annotation file to gather theorems bounding boxes.
        """
        self._data        = {}
        self.LENGTH_LIMIT = 200 # Ignore results that could have captured the whole document.
        self.ordered_blocks = []
        self.res_by_pages = dict()
        
        # uri:(theorem\.(\w+)|proof)\.([0-9]+)
        extraction_re = re.compile(r"uri:(theorem\.([\w\s]*)|proof)\.([0-9]+)",re.IGNORECASE)
        for annotation in xml_annot.findall(".//ANNOTATION/ACTION[@type='uri']/.."):
            dest = annotation.find("ACTION/DEST")
            link_theorem_match = extraction_re.search(dest.text)
            if link_theorem_match is None:
                continue

            if link_theorem_match.group(1) == "proof":
                kind = "proof"
            else:
                kind = link_theorem_match.group(2) 

            if kind not in self._data:
                self._data[kind] = {}

            index   = int(link_theorem_match.group(3))

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
            
            # We remove extra blocks below each theorem/proof
            if max_h-min_h > 8 or not(merge_all):
                self._data[kind][index].append(BBX(page_num, min_h, min_v, max_h, max_v))

        # We merge box for the same theorem and on the same page
        if merge_all:
            for (kind, results) in self._data.items():
                for result_id, bbxes in results.items():
                    if len(bbxes) > self.LENGTH_LIMIT:
                        self._data[kind][result_id] = []
                        continue
                    res_boxlist = []
                    curr_box = None
                    for bbx in bbxes:
                        if curr_box == None:
                            curr_box = bbx
                        elif curr_box.page_num == bbx.page_num \
                             and abs(curr_box.max_h-bbx.max_h) <= 100: # for bicolumns
                            curr_box.group_with(bbx)
                        else:
                            res_boxlist.append(curr_box)
                            curr_box = bbx
                    res_boxlist.append(curr_box)
                    self._data[kind][result_id] = res_boxlist
            
            idx = 0
            for (kind, results) in self._data.items():
                    for result_id, bbxes in results.items():
                        for i,bbx in enumerate(bbxes):
                            
                            page_n = int(bbx.page_num)
                            self.ordered_blocks.append({"kind":kind,
                                                        "result":result_id,
                                                        "bbx":bbx})

                            
                            if page_n not in self.res_by_pages:
                                self.res_by_pages[page_n] = {"idx":[],"pos":[]}

                            self.res_by_pages[page_n]["idx"].append(idx)
                            self.res_by_pages[page_n]["pos"].append([(bbx.min_v+bbx.max_v)/2])
                            idx += 1

            for page in self.res_by_pages:
                self.res_by_pages[page]["tree"] = KDTree(self.res_by_pages[page]["pos"])


   
    def get_kind(self, node, mode="full", kind="node",max_neighbors=5,extend_size=10):
        """
        Get the type of a node, containing HPOS, VPOS, HEIGHT, WIDTH fields.
        Mode can be either 'intersect' or 'full'.
        Returns Theorem|Lemma|Proposition|Definition|proof|Text
        """

        pos_v =  float(node.get("VPOS")) + float(node.get("HEIGHT"))/2
        pos_h = float(node.get("HPOS")) + float(node.get("WIDTH"))/2
        point = { 'h': pos_h,
                  'v': pos_v }

        while kind == "node" and node.tag != f"{ALTO}Page":
            node = node.getparent()
        
        
        page_num  = node.get("PHYSICAL_IMG_NR")
        page_n = int(page_num)

        if page_n not in self.res_by_pages:
            return "Text",None

        
        tree = self.res_by_pages[page_n]["tree"]
        _,neighbors = tree.query([pos_v],max_neighbors)
        if max_neighbors == 1:
            neighbors = [neighbors]
        
        for i_n,neighbor in enumerate(neighbors):
            if neighbor >= len(self.res_by_pages[page_n]["idx"]):
                break
            idx = self.res_by_pages[page_n]["idx"][neighbor]
            res = self.ordered_blocks[idx]
            bbx = res["bbx"]

            if bbx.contains_point(point):
                return res["kind"], res["result"]

        return "Text", None

    

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
    return pix
    
def render_result(bounding_boxes, pdf, context=50):
    bbxs = BBX.from_list(bounding_boxes)
    for bbx in bbxs:
        pix = render_box(bbx.extend(context), pdf)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        print(">>", pix.width, pix.height)
        for boxes in bbx.parents:
            min_h,max_h = int(context+boxes.min_h-bbx.min_h), int(context+boxes.max_h-bbx.min_h)
            min_v,max_v = int(context+boxes.min_v-bbx.min_v), int(context+boxes.max_v-bbx.min_v)
            print(min_h,max_h,min_v,max_v)
            
            for x in range(min_h, max_h):
                img.putpixel((x,min_v),(255, 0, 0))
                img.putpixel((x,max_v),(255, 0, 0))

            for y in range(min_v,max_v):
                img.putpixel((min_h,y),(255, 0, 0))
                img.putpixel((max_h,y),(255, 0, 0))
 
        img.show()
