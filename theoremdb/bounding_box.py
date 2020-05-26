from copy import copy

class BBX:
    """
    Bounding box in a PDF.
    """

    def __init__(self, page_num, min_h, min_v, max_h, max_v):
        self.page_num = page_num
        self.min_h = min_h
        self.min_v = min_v
        self.max_h = max_h
        self.max_v = max_v
    
    def contains(self, other):
        """
        Check if this bounding box contains the other.
        """
        return self.page_num == other.page_num \
            and other.min_h >= self.min_h \
            and other.min_v >= self.min_v \
            and other.max_h <= self.max_h \
            and other.max_v <= self.max_v

    def intersects(self, other):
        """
        Check if this bounding box intersects the other. 
        """
        return self.page_num == other.page_num \
            and other.max_h >= self.min_h \
            and self.max_h >= other.min_h \
            and other.max_v >= self.min_v \
            and self.max_v >= other.min_v
    
    def group_with(self, other):
        """
        Inplace merge two bounding boxes from the same page.
        """
        assert self.page_num == other.page_num
        self.min_h = min(self.min_h, other.min_h)
        self.max_h = max(self.max_h, other.max_h)
        self.min_v = min(self.min_v, other.min_v)
        self.max_v = max(self.max_v, other.max_v)
    
    def extend(self, d):
        copied = copy(self)
        copied.min_h -= d
        copied.max_h += d
        copied.min_v -= d
        copied.max_v += d
        return copied
        
    @staticmethod
    def from_list(lst):
        by_page = {}
        
        for b in lst:
            if b.page_num not in by_page:
                by_page[b.page_num] = b
            else:
                by_page[b.page_num].group_with(b)
    
        return by_page.values()
