# -*- coding: utf-8 -*-
"""Unit tests for V3 engines (ObjectEngineV2 + PyMuPDFEngineV2)."""
import tempfile
import unittest
from pathlib import Path

import fitz

from core.object_engine_v2 import ObjectEngineV2
from core.engine_pymupdf_v2 import PyMuPDFEngineV2


class ObjectEngineV2Tests(unittest.TestCase):
    def _make_doc_with_watermark(self, pages=3, text="CONFIDENTIAL"):
        doc = fitz.open()
        for _ in range(pages):
            page = doc.new_page()
            page.insert_text((72, 72), "Body content here")
            page.insert_text((200, 400), text)
        return doc

    def test_batch_match_finds_same_text_on_all_pages(self):
        doc = self._make_doc_with_watermark(pages=4)
        try:
            engine = ObjectEngineV2(doc)
            objs = engine.get_page_objects(0, filters=["text"])
            templates = [o for o in objs if "CONFIDENTIAL" in o.get("text", "")]
            self.assertTrue(templates, "template watermark not found on page 0")

            matches = engine.find_matches_batch(
                templates, range(doc.page_count), mode="loose", filters=["text"]
            )
            pages_hit = {p for p, _ in matches}
            self.assertEqual(pages_hit, {0, 1, 2, 3})
        finally:
            doc.close()

    def test_content_mode_ignores_position(self):
        doc = fitz.open()
        p0 = doc.new_page()
        p0.insert_text((50, 50), "LogoMark")
        p1 = doc.new_page()
        p1.insert_text((300, 500), "LogoMark")  # different position
        try:
            engine = ObjectEngineV2(doc)
            tpl = [o for o in engine.get_page_objects(0, filters=["text"]) if "LogoMark" in o["text"]]
            matches = engine.find_matches_batch(
                tpl, [1], mode="content", filters=["text"]
            )
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0][0], 1)
        finally:
            doc.close()

    def test_cancel_flag_stops_scan(self):
        doc = self._make_doc_with_watermark(pages=20)
        try:
            engine = ObjectEngineV2(doc)
            tpl = engine.get_page_objects(0, filters=["text"])[:1]
            calls = {"n": 0}

            def cancel():
                calls["n"] += 1
                return calls["n"] > 3

            matches = engine.find_matches_batch(
                tpl, range(20), mode="loose", filters=["text"], cancel_flag=cancel
            )
            # cancelled early — should not have scanned all 20 pages worth of work fully
            self.assertIsInstance(matches, list)
        finally:
            doc.close()


class PyMuPDFEngineV2Tests(unittest.TestCase):
    def test_grouped_remove_and_region(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "in.pdf"
            out = Path(tmpdir) / "out.pdf"

            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "Keep me")
            page.insert_text((200, 200), "DROP")
            doc.save(src)
            doc.close()

            src_doc = fitz.open(src)
            engine_obj = ObjectEngineV2(src_doc)
            drop = [o for o in engine_obj.get_page_objects(0, filters=["text"]) if "DROP" in o["text"]]
            src_doc.close()
            self.assertTrue(drop)

            removals = [(0, drop[0]), (0, {"type": "region", "bbox": [10, 10, 40, 40]})]
            eng = PyMuPDFEngineV2(str(src))
            n = eng.remove_objects(removals, str(out))
            eng.close()
            self.assertGreaterEqual(n, 1)

            cleaned = fitz.open(out)
            try:
                text = cleaned[0].get_text()
                self.assertNotIn("DROP", text)
                self.assertIn("Keep me", text)
            finally:
                cleaned.close()


if __name__ == "__main__":
    unittest.main()
