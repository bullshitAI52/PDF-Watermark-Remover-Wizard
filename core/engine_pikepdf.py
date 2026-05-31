# -*- coding: utf-8 -*-
import pikepdf

from .scanner import normalize_text


def _get_color_type(operands):
    """Classify PDF color operands into broad buckets used by vector cleanup."""
    try:
        vals = [float(x) for x in operands]
    except Exception:
        return "OTHER"

    if len(vals) == 1:
        value = vals[0]
        if 0.49 <= value <= 0.51:
            return "BLUE"
        if value < 0.1:
            return "BLACK"
        if 0.1 <= value <= 0.95:
            return "GRAY"

    elif len(vals) == 3:
        r, g, b = vals
        if b > 0.8 and b > r:
            return "BLUE"
        if b > 0.4 and b > r + 0.1:
            return "BLUE"
        if r > 0.9 and g < 0.1 and b < 0.1:
            return "RED"
        if r < 0.1 and g < 0.1 and b < 0.1:
            return "BLACK"
        if abs(r - g) < 0.1 and abs(g - b) < 0.1 and 0.1 < r < 0.95:
            return "GRAY"

    elif len(vals) == 4:
        c, m, y, k = vals
        if k > 0.9:
            return "BLACK"
        if c > 0.5 and y < 0.1:
            return "BLUE"
        if 0.1 < k < 0.9 and c < 0.1:
            return "GRAY"

    return "OTHER"

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
        op = str(operator)
        text = self._extract_text(op, operands)
        if not text:
            return False

        for t in targets:
            if t in text:
                return True

        norm_text = normalize_text(text)
        for tn in target_norms:
            if tn and tn in norm_text:
                return True

        return False

    def _extract_text(self, operator, operands):
        if not operands:
            return ""

        if operator in ["Tj", "'", '"']:
            return self._stringify_text_operand(operands[0])

        if operator == "TJ" and isinstance(operands[0], (list, pikepdf.Array)):
            return "".join(
                self._stringify_text_operand(item)
                for item in operands[0]
                if isinstance(item, (str, bytes, pikepdf.String))
            )

        return ""

    def _stringify_text_operand(self, value):
        if isinstance(value, bytes):
            try:
                return value.decode("utf-8", errors="ignore")
            except Exception:
                return ""
        return str(value)

    def remove_vector_objects(self, output_path, target_gray=False):
        """Nuclear mode: removes vector paths and shapes."""
        total_removed = 0

        for page in self.pdf.pages:
            try:
                commands = pikepdf.parse_content_stream(page)
                new_cmds = []
                stack = []
                current_fill_type = "BLACK"
                current_stroke_type = "BLACK"

                for operands, operator in commands:
                    op = str(operator)

                    if op == "q":
                        stack.append((current_fill_type, current_stroke_type))
                    elif op == "Q":
                        if stack:
                            current_fill_type, current_stroke_type = stack.pop()
                        else:
                            current_fill_type = "BLACK"
                            current_stroke_type = "BLACK"
                    elif op in ["sc", "scn", "g", "rg", "k"]:
                        current_fill_type = _get_color_type(operands)
                    elif op in ["SC", "SCN", "G", "RG", "K"]:
                        current_stroke_type = _get_color_type(operands)

                    if self._should_remove_vector_op(op, current_fill_type, current_stroke_type, target_gray):
                        total_removed += 1
                        continue

                    new_cmds.append((operands, operator))

                page.Contents = self.pdf.make_stream(pikepdf.unparse_content_stream(new_cmds))
            except Exception:
                continue

        self.pdf.save(output_path)
        return total_removed

    def _should_remove_vector_op(self, op, fill_type, stroke_type, target_gray):
        if op in ["f", "F", "f*"]:
            return fill_type in ["BLUE", "RED", "BLACK"] or (target_gray and fill_type == "GRAY")

        if op in ["S", "s"]:
            return stroke_type in ["BLUE", "RED"] or (target_gray and stroke_type == "GRAY")

        if op in ["B", "B*", "b", "b*"]:
            if fill_type in ["BLUE", "RED", "BLACK"]:
                return True
            if stroke_type in ["BLUE", "RED"]:
                return True
            if target_gray and (fill_type == "GRAY" or stroke_type == "GRAY"):
                return True

        return False

    def close(self):
        self.pdf.close()
