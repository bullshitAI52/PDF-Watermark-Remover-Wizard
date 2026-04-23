# -*- coding: utf-8 -*-
import fitz
import os

class PyMuPDFEngine:
    def __init__(self, input_path):
        self.input_path = input_path
        self.doc = fitz.open(input_path)

    def remove_regions(self, regions, output_path, fill_color=(1, 1, 1)):
        """Removes specified rectangular regions from the PDF."""
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            has_redactions = False
            
            for region in regions:
                # region should be a list/tuple: [x0, y0, x1, y1]
                rect = fitz.Rect(region)
                page.add_redact_annot(rect, fill=fill_color)
                has_redactions = True
                
            if has_redactions:
                page.apply_redactions()
        
        self.doc.save(output_path, garbage=3, deflate=True)

    def remove_text(self, targets, output_path):
        """Removes specific text strings using redaction."""
        for page in self.doc:
            has_redactions = False
            for text in targets:
                if not text.strip(): continue
                instances = page.search_for(text.strip())
                for rect in instances:
                    page.add_redact_annot(rect, fill=(1, 1, 1))
                    has_redactions = True
            
            if has_redactions:
                page.apply_redactions()
        
        self.doc.save(output_path, garbage=3, deflate=True)

    def get_page_pixmap(self, page_idx, zoom=2.0):
        page = self.doc[page_idx]
        return page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))

    def remove_objects(self, object_list, output_path):
        """Removes specific objects based on their properties."""
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            has_redactions = False
            
            # This is a bit complex as we need to find the object again on the page
            # For now, we'll use the bbox provided in the object list if it's for this page
            for page_idx, obj in object_list:
                if page_idx == page_num:
                    rect = fitz.Rect(obj["bbox"])
                    page.add_redact_annot(rect, fill=(1, 1, 1))
                    has_redactions = True
                    
            if has_redactions:
                page.apply_redactions()
        
        self.doc.save(output_path, garbage=3, deflate=True)

    def close(self):
        self.doc.close()
