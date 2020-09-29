import re, sys
from .bounding_box import BBX
from scipy.spatial.kdtree import KDTree



ALTO = "{http://www.loc.gov/standards/alto/ns-v3#}"


class RefsBBX:
    """
    Extract boxes for links in the pdf from the xml_annot
    """
    def __init__(self, xml_annot):

        self._data        = []
        self.ref_by_pages = {}
        idx = 0

        for annotation in xml_annot.findall(".//ANNOTATION/ACTION[@type='goto']/.."):
            dest = annotation.find("ACTION/DEST")
            try: 
                page_dest = dest.get("page")
                x_dest = dest.get("x")
                y_dest = dest.get("y")
            except:
                # Maybe change that, see how much we loose
                continue

            page_num = annotation.get("pagenum")
            page_n = int(page_num)

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
            
            self._data.append({
                    "page_dest":page_dest,
                    "x_dest":x_dest,
                    "y_dest":y_dest,
                    "bbx":BBX(page_num, min_h, min_v, max_h, max_v)
                    } )

            """ 
            Add a new point in the QDTree of the page *page_n*
            """
            if page_n not in self.ref_by_pages:
                self.ref_by_pages[page_n] = {"idx":[],"pos":[]}
            
            self.ref_by_pages[page_n]["idx"].append(idx)
            self.ref_by_pages[page_n]["pos"].append([(min_v+max_v)/2,(min_h+max_h)/2])
            idx += 1
                

        # Convert list to QDTree
        for page in self.ref_by_pages:
            self.ref_by_pages[page]["tree"] = KDTree(self.ref_by_pages[page]["pos"])
                            
                            




    def get_dest(self, node, max_neighbors=5,extend_size=2):

        min_h, min_v = float(node.get("HPOS")), float(node.get("VPOS"))
        max_h, max_v = min_h + float(node.get("WIDTH")), min_v + float(node.get("HEIGHT"))


        while node.tag != f"{ALTO}Page":
            node = node.getparent()
        
        page_num  = node.get("PHYSICAL_IMG_NR")
        page_n = int(page_num)
        if page_n not in self.ref_by_pages:
            return -1,None

        pos_h = (min_h+max_h)/2
        pos_v = (min_v+max_v)/2
 
        point = {'h':pos_h,'v':pos_v}
        tree = self.ref_by_pages[page_n]["tree"]
        _,neighbors = tree.query([pos_v,pos_h],max_neighbors)

        if max_neighbors == 1:
            neighbors = [neighbors]

        for i_n,neighbor in enumerate(neighbors):
            if neighbor >= len(self.ref_by_pages[page_n]["idx"]):
                break
            idx = self.ref_by_pages[page_n]["idx"][neighbor]
            res = self._data[idx]
            bbx = res["bbx"]

            if bbx.extend(extend_size).contains_point(point):
                return idx, res

        return -1, None
        
    


