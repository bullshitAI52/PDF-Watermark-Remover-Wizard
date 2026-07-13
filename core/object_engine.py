# -*- coding: utf-8 -*-
import fitz

class ObjectEngine:
    """Enhanced Forensic engine to extract and index objects from a PDF page."""
    
    def __init__(self, doc):
        self.doc = doc
        self._page_cache = {}

    def invalidate_cache(self):
        self._page_cache.clear()

    def get_page_objects(self, page_idx, filters=None):
        """Extracts all objects from a page, with improved drawing support."""
        key = (page_idx, tuple(filters) if filters else None)
        if key in self._page_cache:
            return self._page_cache[key]

        page = self.doc[page_idx]
        objects = []
        
        if filters is None:
            filters = ["text", "image", "drawing"]

        # 1. Extract Text (Span-level)
        if "text" in filters:
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                if block["type"] == 0:  # Text block
                    for line in block["lines"]:
                        for span in line["spans"]:
                            objects.append({
                                "type": "text",
                                "bbox": list(span["bbox"]),
                                "text": span["text"],
                                "font": span["font"],
                                "size": span["size"],
                                "color": span["color"]
                            })

        # 2. Extract Images (XObject level)
        if "image" in filters:
            img_list = page.get_images(full=True)
            for img in img_list:
                xref = img[0]
                rects = page.get_image_rects(xref)
                for r in rects:
                    objects.append({
                        "type": "image",
                        "bbox": list(r),
                        "xref": xref,
                        "width": img[2],
                        "height": img[3]
                    })

        # 3. Extract Drawings (Vector Paths - Robust mode)
        if "drawing" in filters:
            # page.get_drawings() can be slow for complex PDFs, but it's necessary for stylized watermarks
            drawings = page.get_drawings()
            for draw in drawings:
                rect = draw.get("rect")
                if rect and not rect.is_empty and rect.width > 2 and rect.height > 2:
                    # Ignore tiny dots, focus on shapes
                    objects.append({
                        "type": "drawing",
                        "bbox": list(rect),
                        "items": draw.get("items"), # Path components
                        "color": draw.get("color"),
                        "fill": draw.get("fill"),
                        "width": rect.width,
                        "height": rect.height
                    })

        self._page_cache[key] = objects
        return objects

    def find_matches(self, template_obj, search_pages):
        """Finds objects matching the template with tolerance and property checking."""
        matches = []
        t_type = template_obj["type"]
        
        # Tolerance for position
        tol_pos = 5.0
        # Tolerance for size
        tol_size = 2.0
        
        for page_idx in search_pages:
            objs = self.get_page_objects(page_idx, filters=["text", "image", "drawing"])
            for obj in objs:
                if obj["type"] != t_type:
                    continue
                if self._is_match(template_obj, obj, tol_pos, tol_size):
                    matches.append((page_idx, obj))
        return matches

    def _is_match(self, t, o, tol_pos, tol_size):
        if t["type"] != o["type"]: return False
        
        # Check size (width/height)
        t_w = t["bbox"][2] - t["bbox"][0]
        t_h = t["bbox"][3] - t["bbox"][1]
        o_w = o["bbox"][2] - o["bbox"][0]
        o_h = o["bbox"][3] - o["bbox"][1]
        
        if abs(t_w - o_w) > tol_size or abs(t_h - o_h) > tol_size:
            return False

        # Check Position (Relative or Absolute)
        # For now, absolute position with tolerance
        if abs(t["bbox"][0] - o["bbox"][0]) > tol_pos or abs(t["bbox"][1] - o["bbox"][1]) > tol_pos:
            return False
        
        # Content specifics
        if t["type"] == "text":
            return t["text"] == o["text"]
        elif t["type"] == "drawing":
            # Match by color/fill if available
            return t.get("color") == o.get("color") and t.get("fill") == o.get("fill")
            
        return True
