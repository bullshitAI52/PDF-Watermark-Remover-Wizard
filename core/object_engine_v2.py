# -*- coding: utf-8 -*-
"""ObjectEngine V2 — faster batch matching with configurable tolerance.

Does not replace core.object_engine.ObjectEngine (V1 remains unchanged).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import fitz

from core.scanner import normalize_text

ProgressCb = Optional[Callable[[int, int, str], None]]
MatchMode = str  # "strict" | "loose" | "content"


class ObjectEngineV2:
    """Forensic object extractor with page-once batch matching."""

    def __init__(self, doc: fitz.Document):
        self.doc = doc
        self._page_cache: Dict[Tuple[int, Tuple[str, ...]], List[Dict[str, Any]]] = {}

    def invalidate_cache(self) -> None:
        self._page_cache.clear()

    def get_page_objects(
        self,
        page_idx: int,
        filters: Optional[Sequence[str]] = None,
    ) -> List[Dict[str, Any]]:
        filt = tuple(filters) if filters else ("text", "image", "drawing")
        key = (page_idx, filt)
        if key in self._page_cache:
            return self._page_cache[key]

        page = self.doc[page_idx]
        objects: List[Dict[str, Any]] = []

        if "text" in filt:
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        objects.append(
                            {
                                "type": "text",
                                "bbox": list(span["bbox"]),
                                "text": span.get("text", ""),
                                "font": span.get("font", ""),
                                "size": span.get("size", 0),
                                "color": span.get("color"),
                            }
                        )

        if "image" in filt:
            for img in page.get_images(full=True):
                xref = img[0]
                for r in page.get_image_rects(xref):
                    objects.append(
                        {
                            "type": "image",
                            "bbox": list(r),
                            "xref": xref,
                            "width": img[2],
                            "height": img[3],
                        }
                    )

        if "drawing" in filt:
            for draw in page.get_drawings():
                rect = draw.get("rect")
                if not rect or rect.is_empty or rect.width <= 2 or rect.height <= 2:
                    continue
                items = draw.get("items") or []
                objects.append(
                    {
                        "type": "drawing",
                        "bbox": list(rect),
                        "items": items,
                        "color": draw.get("color"),
                        "fill": draw.get("fill"),
                        "width": rect.width,
                        "height": rect.height,
                        "path_sig": self._path_signature(items),
                    }
                )

        self._page_cache[key] = objects
        return objects

    @staticmethod
    def _path_signature(items: Any) -> str:
        """Compact structural fingerprint of vector path items."""
        if not items:
            return ""
        parts: List[str] = []
        for it in items[:24]:
            try:
                op = it[0] if isinstance(it, (list, tuple)) and it else "?"
                parts.append(str(op))
            except Exception:
                parts.append("?")
        return "|".join(parts)

    def find_matches(
        self,
        template_obj: Dict[str, Any],
        search_pages: Iterable[int],
        *,
        mode: MatchMode = "loose",
        tol_pos: Optional[float] = None,
        tol_size: Optional[float] = None,
    ) -> List[Tuple[int, Dict[str, Any]]]:
        return self.find_matches_batch(
            [template_obj],
            search_pages,
            mode=mode,
            tol_pos=tol_pos,
            tol_size=tol_size,
        )

    def find_matches_batch(
        self,
        templates: Sequence[Dict[str, Any]],
        search_pages: Iterable[int],
        *,
        mode: MatchMode = "loose",
        tol_pos: Optional[float] = None,
        tol_size: Optional[float] = None,
        filters: Optional[Sequence[str]] = None,
        progress_cb: ProgressCb = None,
        cancel_flag: Optional[Callable[[], bool]] = None,
    ) -> List[Tuple[int, Dict[str, Any]]]:
        """Scan each page once; match against all templates.

        Complexity: O(pages × objects × templates) without re-parsing drawings.
        """
        if not templates:
            return []

        if tol_pos is None:
            tol_pos = 5.0 if mode == "strict" else (18.0 if mode == "loose" else 1e9)
        if tol_size is None:
            tol_size = 2.0 if mode == "strict" else (8.0 if mode == "loose" else 1e9)

        needed_types = {t.get("type", "") for t in templates}
        if filters is None:
            filters = [t for t in ("text", "image", "drawing") if t in needed_types]
            if not filters:
                filters = ["text", "image", "drawing"]

        pages = list(search_pages)
        total = len(pages)
        matches: List[Tuple[int, Dict[str, Any]]] = []
        seen: set = set()

        for i, page_idx in enumerate(pages):
            if cancel_flag and cancel_flag():
                break

            if progress_cb:
                progress_cb(i + 1, total, f"扫描第 {page_idx + 1} 页")

            page_w = page_h = None
            try:
                rect = self.doc[page_idx].rect
                page_w, page_h = float(rect.width), float(rect.height)
            except Exception:
                pass

            objs = self.get_page_objects(page_idx, filters=filters)
            for obj in objs:
                if obj.get("type") not in needed_types:
                    continue
                for tpl in templates:
                    if tpl.get("type") != obj.get("type"):
                        continue
                    if not self.is_match(
                        tpl,
                        obj,
                        tol_pos=tol_pos,
                        tol_size=tol_size,
                        mode=mode,
                        page_size=(page_w, page_h),
                    ):
                        continue
                    key = self.obj_key(page_idx, obj)
                    if key in seen:
                        continue
                    seen.add(key)
                    matches.append((page_idx, obj))
                    break

        return matches

    def is_match(
        self,
        t: Dict[str, Any],
        o: Dict[str, Any],
        *,
        tol_pos: float = 5.0,
        tol_size: float = 2.0,
        mode: MatchMode = "loose",
        page_size: Optional[Tuple[Optional[float], Optional[float]]] = None,
    ) -> bool:
        if t.get("type") != o.get("type"):
            return False

        t_w = t["bbox"][2] - t["bbox"][0]
        t_h = t["bbox"][3] - t["bbox"][1]
        o_w = o["bbox"][2] - o["bbox"][0]
        o_h = o["bbox"][3] - o["bbox"][1]

        if mode != "content":
            if abs(t_w - o_w) > tol_size or abs(t_h - o_h) > tol_size:
                return False

            # Absolute position with tolerance
            abs_ok = (
                abs(t["bbox"][0] - o["bbox"][0]) <= tol_pos
                and abs(t["bbox"][1] - o["bbox"][1]) <= tol_pos
            )

            # Relative position (fraction of page) — helps shifted margins
            rel_ok = False
            if page_size and page_size[0] and page_size[1] and page_size[0] > 0 and page_size[1] > 0:
                pw, ph = page_size
                rel_tol = max(tol_pos / max(pw, ph), 0.015 if mode == "loose" else 0.008)
                tx = (t["bbox"][0] + t["bbox"][2]) / 2 / pw
                ty = (t["bbox"][1] + t["bbox"][3]) / 2 / ph
                ox = (o["bbox"][0] + o["bbox"][2]) / 2 / pw
                oy = (o["bbox"][1] + o["bbox"][3]) / 2 / ph
                rel_ok = abs(tx - ox) <= rel_tol and abs(ty - oy) <= rel_tol

            if not abs_ok and not rel_ok:
                return False

        return self._content_match(t, o, mode=mode)

    def _content_match(self, t: Dict[str, Any], o: Dict[str, Any], *, mode: MatchMode) -> bool:
        t_type = t.get("type")
        if t_type == "text":
            tt = t.get("text", "")
            ot = o.get("text", "")
            if mode == "strict":
                return tt == ot
            # loose / content: normalized equality
            nt, no = normalize_text(tt), normalize_text(ot)
            if nt and no and nt == no:
                return True
            if mode == "content" and nt and no and (nt in no or no in nt):
                return True
            # optional font/size soft check when text empty-ish
            if not nt and not no:
                return abs(float(t.get("size", 0) or 0) - float(o.get("size", 0) or 0)) <= 1.0
            return tt == ot

        if t_type == "image":
            if t.get("xref") is not None and o.get("xref") is not None:
                if t["xref"] == o["xref"]:
                    return True
            # fallback: size already checked; accept same-type geometry match
            return mode != "strict" or (
                t.get("width") == o.get("width") and t.get("height") == o.get("height")
            )

        if t_type == "drawing":
            color_ok = t.get("color") == o.get("color") and t.get("fill") == o.get("fill")
            if mode == "strict":
                return color_ok and t.get("path_sig", "") == o.get("path_sig", "")
            if t.get("path_sig") and o.get("path_sig") and t["path_sig"] == o["path_sig"]:
                return True
            return color_ok

        if t_type == "region":
            # Free-form regions are not auto-matched across pages by content
            return False

        return True

    @staticmethod
    def obj_key(page_idx: Optional[int], obj: Dict[str, Any]) -> str:
        b = obj.get("bbox") or [0, 0, 0, 0]
        base = (
            f"{obj.get('type', '?')}|"
            f"{b[0]:.1f}|{b[1]:.1f}|{b[2]:.1f}|{b[3]:.1f}|"
            f"{obj.get('text', '')}|{obj.get('xref', '')}"
        )
        if page_idx is None:
            return base
        return f"{page_idx}|{base}"
