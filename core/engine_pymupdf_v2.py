# -*- coding: utf-8 -*-
"""PyMuPDFEngine V2 — grouped redaction + free-region support.

Does not replace core.engine_pymupdf.PyMuPDFEngine (V1 remains unchanged).

Precision notes:
- text: prefer search_for hits that overlap the marked bbox (avoids wiping
  neighboring text that only shares a loose outer rectangle)
- image / drawing / region: redact the clipped bbox only
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import fitz
from core.scanner import normalize_text


class PyMuPDFEngineV2:
    def __init__(self, input_path: str):
        self.input_path = input_path
        self.doc = fitz.open(input_path)

    def remove_objects(
        self,
        object_list: Sequence[Tuple[int, Dict[str, Any]]],
        output_path: str,
        fill_color: Tuple[float, float, float] = (1, 1, 1),
        images: bool = True,
        precise_text: bool = True,
    ) -> int:
        """Remove objects grouped by page (single apply_redactions per page).

        Supports object types: text, image, drawing, region (free-form bbox).
        Returns number of redaction annotations applied.
        """
        by_page: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for page_idx, obj in object_list:
            if page_idx is None or obj is None:
                continue
            by_page[int(page_idx)].append(obj)

        total = 0
        for page_num in sorted(by_page.keys()):
            if page_num < 0 or page_num >= len(self.doc):
                continue
            page = self.doc[page_num]
            page_has = False
            for obj in by_page[page_num]:
                n = self._redact_one(page, obj, fill_color, precise_text=precise_text)
                if n > 0:
                    page_has = True
                    total += n

            if page_has:
                # images=True removes image content under redaction boxes when possible
                page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS if images else 0)

        self.doc.save(output_path, garbage=3, deflate=True)
        return total

    def _redact_one(
        self,
        page: fitz.Page,
        obj: Dict[str, Any],
        fill_color: Tuple[float, float, float],
        *,
        precise_text: bool = True,
    ) -> int:
        bbox = obj.get("bbox")
        if not bbox or len(bbox) < 4:
            return 0
        target = fitz.Rect(bbox) & page.rect
        if target.is_empty or target.is_infinite:
            return 0

        otype = obj.get("type") or ""

        # Text: only wipe search hits that actually overlap the marked span.
        # Prevents collateral damage when watermark text sits near body text.
        if precise_text and otype == "text":
            text = str(obj.get("text") or "").strip()
            if text:
                count = 0
                # Pre-collect page text words for overlap-safe clipping
                page_words = page.get_text("words")
                for hit in page.search_for(text):
                    inter = hit & target
                    if inter.is_empty:
                        continue
                    # Require meaningful overlap with the user-marked box
                    hit_area = max(hit.get_area(), 1e-6)
                    tgt_area = max(target.get_area(), 1e-6)
                    inter_area = inter.get_area()
                    if inter_area / hit_area >= 0.45 or inter_area / tgt_area >= 0.45:
                        safe = self._clip_against_other_text(hit, text, page_words)
                        if safe is not None and not safe.is_empty and safe.get_area() > 0:
                            page.add_redact_annot(safe, fill=fill_color)
                        elif safe is None:
                            page.add_redact_annot(hit, fill=fill_color)
                        count += 1
                if count:
                    return count
            # Fallback: tight marked bbox only (not expanded)
            page_words = page.get_text("words")
            text = str(obj.get("text") or "").strip()
            if text:
                safe = self._clip_against_other_text(target, text, page_words)
                if safe is not None and not safe.is_empty and safe.get_area() > 0:
                    page.add_redact_annot(safe, fill=fill_color)
                else:
                    page.add_redact_annot(target, fill=fill_color)
            else:
                page.add_redact_annot(target, fill=fill_color)
            return 1

        # Images / drawings / free regions: exact marked rectangle
        page.add_redact_annot(target, fill=fill_color)
        return 1


    @staticmethod
    def _clip_against_other_text(
        rect: fitz.Rect,
        target_text: str,
        page_words: List[tuple],
    ) -> Optional[fitz.Rect]:
        """Clip *rect* to remove portions that overlap with non-target text words.

        PyMuPDF's ``apply_redactions`` removes an entire text word (span-level
        bbox) whenever the redaction rect intersects *any* part of it. This
        means we can clip the redaction rect *away* from non-target text: as
        long as the clipped rect still touches the target word's own bbox, it
        will be fully removed --- but non-target words that only touched the
        clipped-off portion will survive.

        Returns *None* when the rect becomes empty after clipping (caller
        should fall back to the unclipped rect in that case).
        """
        safe = fitz.Rect(rect)
        t_normalized = normalize_text(str(target_text))

        for w in page_words:
            w_rect = fitz.Rect(w[:4])
            w_text = str(w[4])

            # Skip words that match the target (normalized comparison)
            if normalize_text(w_text) == t_normalized:
                continue

            inter = safe & w_rect
            if inter.is_empty or inter.get_area() <= 0:
                continue

            i_x0, i_y0, i_x1, i_y1 = inter.x0, inter.y0, inter.x1, inter.y1
            s_x0, s_y0, s_x1, s_y1 = safe.x0, safe.y0, safe.x1, safe.y1
            w_x0, w_y0, w_x1, w_y1 = w_rect.x0, w_rect.y0, w_rect.x1, w_rect.y1

            # Check if the intersection spans safe's full width (within 1pt tolerance)
            spans_full_width = (i_x0 <= s_x0 + 1) and (i_x1 >= s_x1 - 1)
            spans_full_height = (i_y0 <= s_y0 + 1) and (i_y1 >= s_y1 - 1)

            if spans_full_width and spans_full_height:
                # Other text completely contains safe -> cannot clip to avoid
                return None

            if spans_full_width:
                # Other text spans safe's full width -> clip in y-direction
                if w_y1 >= s_y1:  # other extends below -> clip safe's bottom
                    safe.y1 = min(s_y1, max(i_y0, s_y0))
                if w_y0 <= s_y0:  # other extends above -> clip safe's top
                    safe.y0 = max(s_y0, min(i_y1, s_y1))

            elif spans_full_height:
                # Other text spans safe's full height -> clip in x-direction
                if w_x1 >= s_x1:  # other extends right -> clip safe's right
                    safe.x1 = min(s_x1, max(i_x0, s_x0))
                if w_x0 <= s_x0:  # other extends left -> clip safe's left
                    safe.x0 = max(s_x0, min(i_x1, s_x1))

            else:
                # Partial overlap in both axes --- clip the axis with more overlap
                i_w, i_h = i_x1 - i_x0, i_y1 - i_y0
                if i_h < i_w:
                    if w_y1 >= s_y1:
                        safe.y1 = min(s_y1, max(i_y0, s_y0))
                    elif w_y0 <= s_y0:
                        safe.y0 = max(s_y0, min(i_y1, s_y1))
                else:
                    if w_x1 >= s_x1:
                        safe.x1 = min(s_x1, max(i_x0, s_x0))
                    elif w_x0 <= s_x0:
                        safe.x0 = max(s_x0, min(i_x1, s_x1))

        if safe.is_empty or safe.get_area() <= 0:
            return None
        return safe

    def remove_regions(

        self,
        regions: Iterable[Tuple[int, Sequence[float]]],
        output_path: str,
        fill_color: Tuple[float, float, float] = (1, 1, 1),
    ) -> int:
        """Convenience: regions as (page_idx, [x0,y0,x1,y1])."""
        object_list = [
            (page_idx, {"type": "region", "bbox": list(bbox)})
            for page_idx, bbox in regions
        ]
        return self.remove_objects(object_list, output_path, fill_color=fill_color)

    def remove_text(self, targets: Sequence[str], output_path: str) -> None:
        for page in self.doc:
            has = False
            for text in targets:
                if not text or not str(text).strip():
                    continue
                for rect in page.search_for(str(text).strip()):
                    page.add_redact_annot(rect, fill=(1, 1, 1))
                    has = True
            if has:
                page.apply_redactions()
        self.doc.save(output_path, garbage=3, deflate=True)

    def get_page_pixmap(self, page_idx: int, zoom: float = 2.0):
        page = self.doc[page_idx]
        return page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))

    def close(self) -> None:
        self.doc.close()
