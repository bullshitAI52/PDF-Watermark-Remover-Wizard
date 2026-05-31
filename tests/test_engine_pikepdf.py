import tempfile
import unittest
from pathlib import Path

import fitz
import pikepdf

from core.engine_pikepdf import PikepdfEngine
from core.scanner import normalize_text


class PikepdfEngineTests(unittest.TestCase):
    def test_normalize_text_ignores_spacing_and_punctuation(self):
        self.assertEqual(normalize_text(" A-B C，测试 "), "abc测试")

    def test_remove_text_removes_matching_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "input.pdf"
            out = Path(tmpdir) / "output.pdf"

            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "Hello Watermark")
            doc.save(src)
            doc.close()

            engine = PikepdfEngine(str(src))
            engine.remove_text(["Hello Watermark"], str(out))
            engine.close()

            cleaned = fitz.open(out)
            try:
                self.assertNotIn("Hello Watermark", cleaned[0].get_text())
            finally:
                cleaned.close()

    def test_remove_vector_objects_strips_blue_fill(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "vector.pdf"
            out = Path(tmpdir) / "vector_cleaned.pdf"

            doc = fitz.open()
            page = doc.new_page()
            page.draw_rect(fitz.Rect(50, 50, 150, 150), color=(0, 0, 1), fill=(0, 0, 1))
            doc.save(src)
            doc.close()

            with pikepdf.open(src) as pdf:
                before = len(pikepdf.parse_content_stream(pdf.pages[0]))

            engine = PikepdfEngine(str(src))
            removed = engine.remove_vector_objects(str(out))
            engine.close()

            with pikepdf.open(out) as pdf:
                after = len(pikepdf.parse_content_stream(pdf.pages[0]))

            self.assertGreater(removed, 0)
            self.assertLess(after, before)


if __name__ == "__main__":
    unittest.main()
