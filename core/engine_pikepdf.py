# -*- coding: utf-8 -*-
import pikepdf
import math
import os
from .scanner import normalize_text, estimate_rotation, apply_matrix

class PikepdfEngine:
    def __init__(self, input_path):
        self.input_path = input_path
        self.pdf = pikepdf.open(input_path)

    def remove_text(self, targets, output_path):
        """Removes specific text patterns from the PDF."""
        target_norms = [normalize_text(t) for t in targets if t.strip()]
        
        for page in self.pdf.pages:
            try:
                commands = pikepdf.parse_content_stream(page)
                new_commands = []
                for operands, operator in commands:
                    if self._is_target_text(operands, operator, targets, target_norms):
                        continue
                    new_commands.append((operands, operator))
                
                page.Contents = self.pdf.make_stream(pikepdf.unparse_content_stream(new_commands))
            except Exception:
                continue
        
        self.pdf.save(output_path)

    def _is_target_text(self, operands, operator, targets, target_norms):
        # Logic to check if operands/operator match any target
        # Simplified for now, can be expanded with full is_watermark logic
        op = str(operator)
        text = ""
        if op in ["Tj", "'", "\"" ] and len(operands) > 0:
            text = str(operands[0])
        elif op == "TJ" and len(operands) > 0 and isinstance(operands[0], list):
            text = "".join(str(i) for i in operands[0] if isinstance(i, (str, bytes, pikepdf.String)))
            
        if not text:
            return False
            
        for t in targets:
            if t in text: return True
        
        norm_text = normalize_text(text)
        for tn in target_norms:
            if tn and tn in norm_text: return True
            
        return False

    def remove_vector_objects(self, output_path, target_gray=False):
        """Nuclear mode: removes vector paths and shapes."""
        # Ported from vector_killer.py
        for page in self.pdf.pages:
            try:
                commands = pikepdf.parse_content_stream(page)
                new_cmds = []
                for operands, operator in commands:
                    op = str(operator)
                    # Skip common vector operators if they match certain patterns
                    if op in ["m", "l", "c", "v", "y", "re", "S", "s", "F", "f", "B", "b"]:
                        if target_gray:
                            # Add gray detection logic here
                            pass
                        continue 
                    new_cmds.append((operands, operator))
                page.Contents = self.pdf.make_stream(pikepdf.unparse_content_stream(new_cmds))
            except Exception:
                continue
        self.pdf.save(output_path)

    def close(self):
        self.pdf.close()
