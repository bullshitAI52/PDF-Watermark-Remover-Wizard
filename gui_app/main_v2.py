#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# PDF Watermark Remover Wizard - Visual Pro GUI (V2)
# DISCLAIMER: This tool is for PERSONAL STUDY & RESEARCH ONLY.
# STRICTLY PROHIBITED FOR COMMERCIAL USE or ILLEGAL ACTIVITIES.
# -----------------------------------------------------------------------------
"""
Visual interactive GUI for PDF watermark removal.
Features: object click-select, area box-select, whole-book sync, quick-export.
"""

from __future__ import annotations

import os
import sys
import io
import math
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --- Path setup (support both source and frozen/PyInstaller) ---
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, BASE_DIR)

INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TEMP_DIR = os.path.join(BASE_DIR, "temp_images")

# --- Third-party imports ---
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageTk

try:
    import customtkinter as ctk
except ImportError:
    print("❌ customtkinter not installed. Run: pip install customtkinter")
    sys.exit(1)

# CTkMessagebox causes UI freezes on macOS, removed.

# --- Internal engine imports ---
from core.object_engine import ObjectEngine
from core.engine_pymupdf import PyMuPDFEngine
from utils.config_manager import load_config, save_config, ensure_dirs
from utils.file_utils import get_supported_files

# =============================================================================
# Constants
# =============================================================================
APP_TITLE = "PDF 水印清理助手（旧版兼容）"
DEFAULT_ZOOM = 1.5
MIN_ZOOM = 0.5
MAX_ZOOM = 5.0
ZOOM_STEP = 0.25

# Object display colors
COLOR_DETECTED = "#4A90D9"     # blue border – normal detected object
COLOR_HOVER = "#FF4444"        # red border – mouse hovering
COLOR_SELECTED = "#FF3333"     # red fill – marked for deletion
COLOR_BOX_SELECT = "#00FF00"   # green – area-select rectangle

OBJECT_FILTERS = ["text", "image", "drawing"]


# =============================================================================
# Helper: zoom-aware geometry
# =============================================================================
def scale_bbox(bbox: List[float], zoom: float) -> Tuple[float, float, float, float]:
    """Scale a bounding-box [x0,y0,x1,y1] by zoom factor."""
    return (bbox[0] * zoom, bbox[1] * zoom, bbox[2] * zoom, bbox[3] * zoom)


def point_in_bbox(px: float, py: float, bbox: List[float]) -> bool:
    """Check whether canvas point (px, py) falls inside the bbox."""
    return bbox[0] <= px <= bbox[2] and bbox[1] <= py <= bbox[3]


# =============================================================================
# PDF Page Renderer
# =============================================================================
class PageRenderer:
    """Renders a single PDF page to a PIL Image at a given zoom level."""

    def __init__(self, doc: fitz.Document):
        self._doc = doc
        self._cache: Dict[Tuple[int, float], Image.Image] = {}

    @property
    def page_count(self) -> int:
        return len(self._doc)

    def render(self, page_idx: int, zoom: float = DEFAULT_ZOOM) -> Image.Image:
        """Return a PIL Image of the page (cached)."""
        key = (page_idx, zoom)
        if key in self._cache:
            return self._cache[key]

        page = self._doc[page_idx]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Limit cache size
        if len(self._cache) > 30:
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[key] = img
        return img

    def invalidate(self):
        self._cache.clear()


# =============================================================================
# Main Application
# =============================================================================
class PDFViewerApp(ctk.CTk):
    """Main Pro GUI window for interactive watermark removal."""

    def __init__(self):
        super().__init__()

        # --- Load config ---
        ensure_dirs()
        self._config = load_config()
        win = self._config.get("window", {})
        theme = self._config.get("theme", {})

        # --- Window setup ---
        self.title(APP_TITLE)
        self.geometry(f"{win.get('width', 1400)}x{win.get('height', 900)}")
        if win.get("x") and win.get("y"):
            self.geometry(f"+{win['x']}+{win['y']}")
        if win.get("maximized"):
            self.after(100, lambda: self.state("zoomed"))

        ctk.set_appearance_mode(theme.get("mode", "light"))
        ctk.set_default_color_theme(theme.get("color_theme", "blue"))

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # --- State ---
        self._pdf_path: Optional[str] = None
        self._doc: Optional[fitz.Document] = None
        self._renderer: Optional[PageRenderer] = None
        self._object_engine: Optional[ObjectEngine] = None
        self._current_page: int = 0
        self._zoom: float = DEFAULT_ZOOM

        # Canvas image reference (prevent GC)
        self._tk_image: Any = None
        self._pil_image: Optional[Image.Image] = None
        self._scaled_bboxes: List[Tuple[float, float, float, float]] = []  # cached for hover perf

        # Object tracking
        self._page_objects: List[Dict] = []          # objects on current page
        self._canvas_rects: List[int] = []            # canvas rectangle IDs
        self._marked_objects: List[Dict] = []          # objects marked for deletion
        self._marked_all_pages: List[Tuple[int, Dict]] = []  # (page_idx, obj) synced across all pages
        self._marks_by_page: Dict[int, List[Dict]] = {} # (page_idx -> marked objects)

        # Interaction state
        self._hovered_idx: int = -1
        self._mode: str = "object"  # "object" | "area"
        self._area_start: Optional[Tuple[float, float]] = None
        self._area_rect_id: Optional[int] = None

        # --- Build UI ---
        self._build_ui()
        self._refresh_file_list()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        """Construct the three-panel layout."""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0)  # status bar at top
        self.grid_rowconfigure(1, weight=1)  # canvas expands

        # -- Left sidebar --
        self._sidebar = ctk.CTkFrame(self, width=260, corner_radius=0)
        self._sidebar.grid(row=0, column=0, rowspan=2, sticky="nsw")
        self._sidebar.grid_propagate(False)
        self._build_sidebar()

        # -- Top status bar (more visible) --
        self._status = ctk.CTkFrame(self, height=32, corner_radius=0)
        self._status.grid(row=0, column=1, sticky="new")
        self._status.grid_propagate(False)
        self._build_status_bar()

        # -- Main canvas area --
        self._canvas_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._canvas_frame.grid(row=1, column=1, sticky="nsew")
        self._canvas_frame.grid_rowconfigure(0, weight=1)
        self._canvas_frame.grid_columnconfigure(0, weight=1)
        self._build_canvas_area()

    def _build_sidebar(self):
        """Left panel: file list, page thumbnails, controls."""
        self._sidebar.grid_columnconfigure(0, weight=1)

        # Header
        ctk.CTkLabel(
            self._sidebar, text="PDF 去水印（兼容版）",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, padx=12, pady=(16, 4), sticky="w")

        ctk.CTkLabel(
            self._sidebar, text="建议新用户使用 V3；此版本保留旧操作方式。",
            font=ctk.CTkFont(size=10), text_color="#888888",
        ).grid(row=1, column=0, padx=12, pady=(0, 4), sticky="w")

        # File list
        self._file_listbox = ctk.CTkScrollableFrame(self._sidebar, height=145)
        self._file_listbox.grid(row=2, column=0, padx=8, pady=4, sticky="nsew")
        self._sidebar.grid_rowconfigure(2, weight=0)

        file_actions = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        file_actions.grid(row=3, column=0, padx=8, pady=(2, 8), sticky="ew")
        file_actions.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(file_actions, text="选择 PDF…", command=self._choose_pdf).grid(row=0, column=0, padx=(0, 3), sticky="ew")
        ctk.CTkButton(file_actions, text="刷新列表", command=self._refresh_file_list).grid(row=0, column=1, padx=(3, 0), sticky="ew")

        # Separator
        ctk.CTkLabel(self._sidebar, text="浏览与标记", font=ctk.CTkFont(size=13, weight="bold")).grid(row=4, column=0, padx=12, pady=(2, 0), sticky="w")

        # Page navigation
        nav_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        nav_frame.grid(row=5, column=0, padx=8, pady=4, sticky="ew")
        nav_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self._btn_prev = ctk.CTkButton(
            nav_frame, text="◀", width=40, command=self._prev_page)
        self._btn_prev.grid(row=0, column=0, padx=2)

        self._page_label = ctk.CTkLabel(
            nav_frame, text="第 - / - 页",
            font=ctk.CTkFont(size=13))
        self._page_label.grid(row=0, column=1)

        self._btn_next = ctk.CTkButton(
            nav_frame, text="▶", width=40, command=self._next_page)
        self._btn_next.grid(row=0, column=2, padx=2)

        # Zoom
        zoom_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        zoom_frame.grid(row=6, column=0, padx=8, pady=4, sticky="ew")
        zoom_frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(zoom_frame, text="−", width=30,
                      command=lambda: self._zoom_in_out(-ZOOM_STEP)).grid(row=0, column=0)
        self._zoom_label = ctk.CTkLabel(zoom_frame, text=f"{self._zoom:.0%}")
        self._zoom_label.grid(row=0, column=1)
        ctk.CTkButton(zoom_frame, text="+", width=30,
                      command=lambda: self._zoom_in_out(ZOOM_STEP)).grid(row=0, column=2)

        # Separator
        ctk.CTkLabel(self._sidebar, text="").grid(row=7, column=0)

        # Mode switch
        mode_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        mode_frame.grid(row=8, column=0, padx=8, pady=4, sticky="ew")
        mode_frame.grid_columnconfigure((0, 1), weight=1)

        self._btn_obj_mode = ctk.CTkButton(
            mode_frame, text="🎯 点选对象", command=lambda: self._set_mode("object"))
        self._btn_obj_mode.grid(row=0, column=0, padx=2, sticky="ew")

        self._btn_area_mode = ctk.CTkButton(
            mode_frame, text="⬜ 区域框选", command=lambda: self._set_mode("area"))
        self._btn_area_mode.grid(row=0, column=1, padx=2, sticky="ew")

        self._mode_label = ctk.CTkLabel(
            mode_frame, text="当前：点选对象（双击标记）",
            font=ctk.CTkFont(size=11))
        self._mode_label.grid(row=1, column=0, columnspan=2, pady=(4, 0))

        # Separator
        ctk.CTkLabel(self._sidebar, text="").grid(row=9, column=0)

        # === Export / Save section ===
        ctk.CTkLabel(
            self._sidebar, text="📤 导出 / 保存",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=10, column=0, padx=12, pady=(4, 2), sticky="w")

        self._btn_save = ctk.CTkButton(
            self._sidebar, text="📥 导出到 output 文件夹", fg_color="#27AE60", hover_color="#219A52",
            command=self._quick_save)
        self._btn_save.grid(row=11, column=0, padx=8, pady=(2, 2), sticky="ew")

        self._btn_save_as = ctk.CTkButton(
            self._sidebar, text="💾 另存为…",
            command=self._save_as)
        self._btn_save_as.grid(row=12, column=0, padx=8, pady=2, sticky="ew")

        # Separator
        ctk.CTkLabel(self._sidebar, text="").grid(row=13, column=0)

        # Action buttons
        self._btn_sync = ctk.CTkButton(
            self._sidebar, text="🌍 全书同步删除", fg_color="#E67E22", hover_color="#D35400",
            command=self._sync_all_pages)
        self._btn_sync.grid(row=14, column=0, padx=8, pady=(4, 2), sticky="ew")

        self._btn_clear = ctk.CTkButton(
            self._sidebar, text="🗑️ 清除当前选中", fg_color="#95A5A6", hover_color="#7F8C8D",
            command=self._clear_marked)
        self._btn_clear.grid(row=15, column=0, padx=8, pady=2, sticky="ew")

        # Stats
        ctk.CTkLabel(self._sidebar, text="").grid(row=16, column=0)
        self._stats_label = ctk.CTkLabel(
            self._sidebar, text="已标记: 0 个对象", font=ctk.CTkFont(size=12))
        self._stats_label.grid(row=17, column=0, padx=8, pady=4)

        # Spacer row so buttons stay at a natural height
        self._sidebar.grid_rowconfigure(18, weight=1)

    def _build_canvas_area(self):
        """Center: scrollable canvas for PDF display."""
        from tkinter import Canvas, Scrollbar, HORIZONTAL, VERTICAL

        # Scrollbars
        self._hbar = Scrollbar(self._canvas_frame, orient=HORIZONTAL)
        self._hbar.grid(row=1, column=0, sticky="ew")
        self._vbar = Scrollbar(self._canvas_frame, orient=VERTICAL)
        self._vbar.grid(row=0, column=1, sticky="ns")

        # Canvas
        self._canvas = Canvas(
            self._canvas_frame,
            bg="#2C2C2C" if ctk.get_appearance_mode() == "Dark" else "#E8E8E8",
            highlightthickness=0,
            xscrollcommand=self._hbar.set,
            yscrollcommand=self._vbar.set,
            cursor="crosshair",
        )
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._hbar.config(command=self._canvas.xview)
        self._vbar.config(command=self._canvas.yview)

        # --- Canvas event bindings ---
        self._canvas.bind("<Motion>", self._on_mouse_move)
        self._canvas.bind("<Double-Button-1>", self._on_double_click)
        self._canvas.bind("<ButtonPress-1>", self._on_button_press)
        self._canvas.bind("<B1-Motion>", self._on_button_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_button_release)
        self._canvas.bind("<Button-2>", self._on_right_click)       # macOS right-click
        self._canvas.bind("<Button-3>", self._on_right_click)       # Windows/Linux right-click
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)

        # Placeholder text
        self._placeholder_id = self._canvas.create_text(
            600, 400, text="📂 请选择一个 PDF 文件\n可点“选择 PDF…”或从 input/ 列表打开",
            font=("Helvetica", 18), fill="#888888")
        self._set_mode(self._mode)

    def _build_status_bar(self):
        """Bottom bar: status messages."""
        self._status_label = ctk.CTkLabel(
            self._status, text="准备就绪", anchor="w", font=ctk.CTkFont(size=11))
        self._status_label.pack(side="left", padx=12, pady=4)

        self._progress_bar = ctk.CTkProgressBar(self._status, width=150)
        self._progress_bar.set(0)
        # Pack dynamically when needed

        self._status_count = ctk.CTkLabel(
            self._status, text="", anchor="e", font=ctk.CTkFont(size=11))
        self._status_count.pack(side="right", padx=12, pady=4)

    # ------------------------------------------------------------------
    # File Management
    # ------------------------------------------------------------------
    def _choose_pdf(self):
        from tkinter import filedialog

        path = filedialog.askopenfilename(
            parent=self,
            title="选择要处理的 PDF",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")],
        )
        if path:
            self._open_pdf(path)

    def _refresh_file_list(self):
        """Scan input/ dir and populate the file list."""
        for w in self._file_listbox.winfo_children():
            w.destroy()

        files = get_supported_files(INPUT_DIR)
        if not files:
            ctk.CTkLabel(
                self._file_listbox,
                text="(没有找到文件)\n请将 PDF 放入 input/ 文件夹",
                font=ctk.CTkFont(size=11),
            ).pack(pady=20)
            return

        for fpath in files:
            fname = os.path.basename(fpath)
            btn = ctk.CTkButton(
                self._file_listbox, text=f"📄 {fname}",
                anchor="w", fg_color="transparent", hover_color="#3498DB",
                command=lambda p=fpath: self._open_pdf(p),
            )
            btn.pack(fill="x", padx=2, pady=1)

    def _open_pdf(self, path: str):
        """Open a PDF file and display the first page."""
        try:
            if self._doc:
                self._doc.close()

            self._pdf_path = path
            self._doc = fitz.open(path)
            self._renderer = PageRenderer(self._doc)
            self._object_engine = ObjectEngine(self._doc)
            self._object_engine.invalidate_cache()
            self._current_page = 0
            self._zoom = DEFAULT_ZOOM
            self._marked_objects.clear()
            self._marked_all_pages.clear()
            self._marks_by_page.clear()

            self._update_zoom_label()
            self._set_status(f"已打开: {os.path.basename(path)}  ({self._doc.page_count} 页)")
            self._display_page()
        except Exception as exc:
            self._set_status(f"❌ 打开失败: {exc}")
            traceback.print_exc()

    # ------------------------------------------------------------------
    # Page Display
    # ------------------------------------------------------------------
    def _display_page(self):
        """Render the current page and overlay detected objects."""
        if not self._doc or not self._renderer or not self._object_engine:
            return

        # Clear canvas (except placeholder)
        self._canvas.delete("all")
        self._canvas_rects.clear()
        self._hovered_idx = -1
        self._placeholder_id = None

        # Render page image
        self._pil_image = self._renderer.render(self._current_page, self._zoom)
        self._tk_image = ImageTk.PhotoImage(
            self._pil_image,
        )
        self._photo_refs = getattr(self, "_photo_refs", []) + [self._tk_image]
        if len(self._photo_refs) > 32:
            self._photo_refs = self._photo_refs[-32:]

        # Place on canvas
        self._img_canvas_id = self._canvas.create_image(
            10, 10, anchor="nw", image=self._tk_image
        )

        # Configure scroll region
        w, h = self._pil_image.width, self._pil_image.height
        self._canvas.config(scrollregion=(0, 0, w + 20, h + 20))

        # Detect and draw objects
        self._page_objects = self._object_engine.get_page_objects(
            self._current_page, filters=OBJECT_FILTERS
        )

        for i, obj in enumerate(self._page_objects):
            sx0, sy0, sx1, sy1 = scale_bbox(obj["bbox"], self._zoom)
            # Offset by 10px canvas margin
            sx0 += 10
            sy0 += 10
            sx1 += 10
            sy1 += 10
            rid = self._canvas.create_rectangle(
                sx0, sy0, sx1, sy1,
                outline=COLOR_DETECTED, width=1, tags=f"obj_{i}"
            )
            self._canvas_rects.append(rid)

        # Pre-compute scaled bboxes for fast hover detection
        self._scaled_bboxes = []
        for obj in self._page_objects:
            sx0, sy0, sx1, sy1 = scale_bbox(obj["bbox"], self._zoom)
            self._scaled_bboxes.append((sx0 + 10, sy0 + 10, sx1 + 10, sy1 + 10))

        # Check which objects are already marked and re-highlight them
        self._redraw_marked()

        # Update labels
        self._page_label.configure(text=f"第 {self._current_page + 1} / {self._doc.page_count} 页")
        total_marked = self._count_all_marks()
        self._stats_label.configure(text=f"已标记: {total_marked} 个对象")
        self._status_count.configure(text=f"检测到 {len(self._page_objects)} 个对象")

    def _redraw_marked(self):
        """Re-apply 'marked' visual state after a redraw."""
        for page_idx, mobj in self._marked_all_pages:
            if page_idx == self._current_page:
                self._highlight_marked_on_canvas(mobj)

        for mobj in self._marked_objects:
            self._highlight_marked_on_canvas(mobj)

    def _highlight_marked_on_canvas(self, obj: Dict):
        """Draw a red-filled rectangle over a marked object's bbox."""
        sx0, sy0, sx1, sy1 = scale_bbox(obj["bbox"], self._zoom)
        self._canvas.create_rectangle(
            sx0 + 10, sy0 + 10, sx1 + 10, sy1 + 10,
            fill=COLOR_SELECTED, outline=COLOR_SELECTED, width=1, stipple="gray25",
            tags="marked",
        )

    # ------------------------------------------------------------------
    # Interaction Handlers
    # ------------------------------------------------------------------
    def _canvas_to_pdf_coords(self, cx: float, cy: float) -> Tuple[float, float]:
        """Convert canvas coordinates back to PDF coordinates."""
        return ((cx - 10) / self._zoom, (cy - 10) / self._zoom)

    def _on_mouse_move(self, event: tk.Event) -> None:  # type: ignore[name-defined]
        """Hover: highlight the object under cursor (uses cached bboxes for speed)."""
        if not self._page_objects or not self._scaled_bboxes:
            return

        # During area drag, skip hover
        if self._area_start is not None:
            return

        found_idx = -1
        mx, my = self._canvas.canvasx(event.x), self._canvas.canvasy(event.y)
        for i, bbox in enumerate(self._scaled_bboxes):
            if bbox[0] <= mx <= bbox[2] and bbox[1] <= my <= bbox[3]:
                found_idx = i
                break

        if found_idx != self._hovered_idx:
            # Reset previous
            if self._hovered_idx >= 0 and self._hovered_idx < len(self._canvas_rects):
                self._canvas.itemconfig(
                    self._canvas_rects[self._hovered_idx], outline=COLOR_DETECTED, width=1)

            self._hovered_idx = found_idx

            # Highlight new
            if found_idx >= 0 and found_idx < len(self._canvas_rects):
                self._canvas.itemconfig(
                    self._canvas_rects[found_idx], outline=COLOR_HOVER, width=2)

    def _on_double_click(self, event: tk.Event) -> None:  # type: ignore[name-defined]
        """Double-click: mark the hovered object for deletion."""
        if not self._page_objects or self._hovered_idx < 0:
            return

        if self._hovered_idx >= len(self._page_objects):
            return

        obj = self._page_objects[self._hovered_idx]
        self._mark_object(obj)

    def _on_button_press(self, event: tk.Event) -> None:  # type: ignore[name-defined]
        """Mouse-down: begin area-select if in area mode."""
        if self._mode != "area":
            return
        self._area_start = (self._canvas.canvasx(event.x), self._canvas.canvasy(event.y))

    def _on_button_drag(self, event: tk.Event) -> None:  # type: ignore[name-defined]
        """Drag: update the selection rectangle."""
        if self._mode != "area" or self._area_start is None:
            return
        sx, sy = self._area_start
        ex, ey = self._canvas.canvasx(event.x), self._canvas.canvasy(event.y)
        if self._area_rect_id is not None:
            self._canvas.delete(self._area_rect_id)
        self._area_rect_id = self._canvas.create_rectangle(
            sx, sy, ex, ey,
            outline=COLOR_BOX_SELECT, width=2, dash=(6, 3),
        )

    def _on_button_release(self, event: tk.Event) -> None:  # type: ignore[name-defined]
        """Mouse-up: finalize area selection and mark enclosed objects."""
        if self._mode != "area" or self._area_start is None:
            return

        # Compute selection rectangle in canvas coords
        sx, sy = self._area_start
        ex, ey = self._canvas.canvasx(event.x), self._canvas.canvasy(event.y)
        rx0, ry0 = min(sx, ex), min(sy, ey)
        rx1, ry1 = max(sx, ex), max(sy, ey)

        # Mark all objects whose center falls inside the rectangle
        marked_count = 0
        for i, obj in enumerate(self._page_objects):
            if i < len(self._scaled_bboxes):
                sbbox = self._scaled_bboxes[i]
                cx = sbbox[0] + (sbbox[2] - sbbox[0]) / 2
                cy = sbbox[1] + (sbbox[3] - sbbox[1]) / 2
            else:
                sbbox = scale_bbox(obj["bbox"], self._zoom)
                cx = sbbox[0] + (sbbox[2] - sbbox[0]) / 2 + 10
                cy = sbbox[1] + (sbbox[3] - sbbox[1]) / 2 + 10
            if rx0 <= cx <= rx1 and ry0 <= cy <= ry1:
                self._mark_object(obj)
                marked_count += 1

        self._set_status(f"区域框选标记了 {marked_count} 个对象")

        # Clean up
        if self._area_rect_id is not None:
            self._canvas.delete(self._area_rect_id)
            self._area_rect_id = None
        self._area_start = None

    def _on_right_click(self, event: tk.Event) -> None:  # type: ignore[name-defined]
        """Right-click: show context menu."""
        from tkinter import Menu

        menu = Menu(self, tearoff=0)

        if self._hovered_idx >= 0 and self._hovered_idx < len(self._page_objects):
            obj = self._page_objects[self._hovered_idx]
            menu.add_command(
                label="🎯 选中/取消此对象",
                command=lambda o=obj: self._mark_object(o))
        else:
            menu.add_command(label="(无对象)", state="disabled")

        menu.add_separator()

        menu.add_command(
            label="🌍 全书同步删除 (匹配所有页面相同水印)",
            command=self._sync_all_pages)

        menu.add_separator()

        menu.add_command(
            label="🗑️ 清除所有标记",
            command=self._clear_marked)

        menu.add_command(
            label="📄 重置当前页",
            command=self._display_page)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _on_mousewheel(self, event: tk.Event) -> None:  # type: ignore[name-defined]
        """Scroll vertically with mouse wheel."""
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ------------------------------------------------------------------
    # Object Marking
    # ------------------------------------------------------------------
    def _mark_object(self, obj: Dict):
        """Toggle object mark for deletion (click again to unmark)."""
        obj_key = self._obj_key(obj)

        # Check if already marked → unmark
        for i, existing in enumerate(self._marked_objects):
            if self._obj_key(existing) == obj_key:
                del self._marked_objects[i]
                # Remove marker visuals from canvas
                self._canvas.delete("marked")
                self._redraw_marked()
                total = self._count_all_marks()
                self._stats_label.configure(text=f"已标记: {total} 个对象")
                self._set_status(f"已取消标记: {obj.get('type', '?')}")
                return

        # Not marked → mark it
        self._marked_objects.append(obj)
        self._highlight_marked_on_canvas(obj)

        total = self._count_all_marks()
        self._stats_label.configure(text=f"已标记: {total} 个对象")
        self._set_status(
            f"已标记: {obj.get('type', '?')} "
            f"\"{obj.get('text', '')[:30]}\" 在 ({obj['bbox'][0]:.1f}, {obj['bbox'][1]:.1f})")

    def _obj_key(self, obj: Dict) -> str:
        """Stable key for dedup."""
        b = obj["bbox"]
        return f"{obj['type']}|{b[0]:.1f}|{b[1]:.1f}|{b[2]:.1f}|{b[3]:.1f}|{obj.get('text', '')}"

    def _count_all_marks(self) -> int:
        """Count marks across all pages."""
        self._marks_by_page[self._current_page] = list(self._marked_objects)
        page_marks = sum(len(marks) for marks in self._marks_by_page.values())
        return page_marks + len(self._marked_all_pages)

    def _clear_marked(self):
        """Clear all marked objects."""
        count = self._count_all_marks()
        self._marked_objects.clear()
        self._marked_all_pages.clear()
        self._marks_by_page.clear()
        self._canvas.delete("marked")
        self._set_status(f"已清除 {count} 个标记")
        self._stats_label.configure(text="已标记: 0 个对象")

    def _sync_all_pages(self):
        """Find matching objects across all pages (after-based batching, no freeze)."""
        # Prevent re-entry
        if getattr(self, '_sync_busy', False):
            return

        # Gather all marked objects across all pages as templates
        self._marks_by_page[self._current_page] = list(self._marked_objects)
        all_templates = []
        for marks in self._marks_by_page.values():
            all_templates.extend(marks)

        if not self._object_engine or not all_templates:
            self._set_status("⚠️ 请先在任意页面单击或框选标记至少一个水印对象。")
            return

        total_pages = self._doc.page_count if self._doc else 0

        # Build batch state
        self._sync_busy = True
        self._sync_templates = list(all_templates)
        self._sync_tpl_idx = 0
        self._sync_remaining = list(range(total_pages))
        self._sync_results = []
        self._sync_total_ops = total_pages * len(self._sync_templates)
        self._sync_done = 0

        self._progress_bar.pack(side="left", padx=10)
        self._progress_bar.set(0)

        self._set_status(f"⏳ 全书同步中 (0/{self._sync_total_ops} 页)...")
        self.update_idletasks()
        self.after(50, self._sync_process_next_page)

    def _sync_process_next_page(self):
        """Process one page, then schedule the next. The 50ms gap keeps the GUI alive."""
        try:
            if not self._doc or self._sync_tpl_idx >= len(self._sync_templates):
                self._sync_finish()
                return

            if not self._sync_remaining:
                self._sync_tpl_idx += 1
                if self._sync_tpl_idx >= len(self._sync_templates):
                    self._sync_finish()
                    return
                self._sync_remaining = list(range(self._doc.page_count))

            page_idx = self._sync_remaining.pop(0)
            template = self._sync_templates[self._sync_tpl_idx]
            t_type = template["type"]

            objs = self._object_engine.get_page_objects(page_idx, filters=[t_type])
            for obj in objs:
                if obj["type"] != t_type:
                    continue
                if self._object_engine._is_match(template, obj, 5.0, 2.0):
                    already = any(
                        page_idx == p and self._obj_key(obj) == self._obj_key(e)
                        for p, e in self._sync_results
                    )
                    if not already:
                        self._sync_results.append((page_idx, obj))

            self._sync_done += 1
            if self._sync_total_ops > 0:
                self._progress_bar.set(self._sync_done / self._sync_total_ops)
            self._set_status(f"⏳ 全书同步中 ({self._sync_done}/{self._sync_total_ops} 页)...")
            self.update_idletasks()
            self.after(50, self._sync_process_next_page)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._set_status(f"❌ 同步出错: {e}")
            self._sync_busy = False

    def _sync_finish(self):
        """Finalize sync results and refresh display."""
        try:
            self._marked_all_pages.extend(self._sync_results)
            total = self._count_all_marks()
            self._stats_label.configure(text=f"已标记: {total} 个对象 (含全书同步)")
            self._set_status(f"🌍 全书同步完成: 新匹配 {len(self._sync_results)} 个对象，共 {total} 个")
            self._display_page()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._set_status(f"❌ 同步完成时出错: {e}")
        finally:
            # Always cleanup
            self._progress_bar.pack_forget()
            for attr in ['_sync_templates', '_sync_tpl_idx', '_sync_remaining', '_sync_results', '_sync_total_ops', '_sync_done']:
                if hasattr(self, attr):
                    delattr(self, attr)
            self._sync_busy = False

    # ------------------------------------------------------------------
    # Save / Export
    # ------------------------------------------------------------------
    def _collect_all_removals(self) -> List[Tuple[int, Dict]]:
        """Merge page-local marks and synced marks into one deduped list."""
        self._marks_by_page[self._current_page] = list(self._marked_objects)
        all_items: List[Tuple[int, Dict]] = []

        # Page-local marks across all pages
        for p_idx, marks in self._marks_by_page.items():
            for obj in marks:
                all_items.append((p_idx, obj))

        # Synced marks across all pages
        all_items.extend(self._marked_all_pages)

        # Dedup
        seen = set()
        unique = []
        for page_idx, obj in all_items:
            k = f"{page_idx}|{self._obj_key(obj)}"
            if k not in seen:
                seen.add(k)
                unique.append((page_idx, obj))
        return unique

    def _quick_save(self):
        """Save to output/ with a default name, no dialog."""
        if not self._pdf_path or not self._doc:
            self._set_status("⚠️ 提示: 请先打开一个 PDF 文件。")
            return

        removals = self._collect_all_removals()
        if not removals:
            self._set_status("⚠️ 提示: 没有标记任何对象，请先标记要删除的水印。")
            return

        base = Path(self._pdf_path).stem
        out_path = os.path.join(OUTPUT_DIR, f"{base}_cleaned.pdf")
        self._do_save(out_path)

    def _save_as(self):
        """Save with a file dialog."""
        if not self._pdf_path or not self._doc:
            self._set_status("⚠️ 提示: 请先打开一个 PDF 文件。")
            return

        removals = self._collect_all_removals()
        if not removals:
            self._set_status("⚠️ 提示: 没有标记任何对象，请先标记要删除的水印。")
            return

        from tkinter import filedialog
        out_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialdir=OUTPUT_DIR,
            initialfile=f"{Path(self._pdf_path).stem}_cleaned.pdf",
        )
        if out_path:
            self._do_save(out_path)

    def _do_save(self, out_path: str):
        """Perform the actual save using PyMuPDFEngine."""
        removals = self._collect_all_removals()
        if not removals:
            return

        self._set_status("⏳ 正在处理并保存，请稍候...")
        self.update_idletasks()

        try:
            # Work on a copy – open the source PDF fresh
            engine = PyMuPDFEngine(self._pdf_path)
            engine.remove_objects(removals, out_path)
            engine.close()

            self._set_status("✅ 提示: 保存成功，已导出到 output 目录。")
        except Exception as exc:
            self._set_status(f"❌ 错误: 保存失败: {exc}")
            import traceback
            traceback.print_exc()

    # ------------------------------------------------------------------
    # Navigation & Zoom
    # ------------------------------------------------------------------
    def _prev_page(self):
        if not self._doc:
            return
        if self._current_page > 0:
            self._marks_by_page[self._current_page] = list(self._marked_objects)
            self._current_page -= 1
            self._marked_objects = list(self._marks_by_page.get(self._current_page, []))
            self._display_page()

    def _next_page(self):
        if not self._doc:
            return
        if self._current_page < self._doc.page_count - 1:
            self._marks_by_page[self._current_page] = list(self._marked_objects)
            self._current_page += 1
            self._marked_objects = list(self._marks_by_page.get(self._current_page, []))
            self._display_page()

    def _zoom_in_out(self, delta: float):
        if not self._doc:
            return
        new_z = self._zoom + delta
        if MIN_ZOOM <= new_z <= MAX_ZOOM:
            self._zoom = new_z
            if self._renderer:
                self._renderer.invalidate()
            self._update_zoom_label()
            self._display_page()

    def _update_zoom_label(self):
        self._zoom_label.configure(text=f"{self._zoom:.0%}")

    # ------------------------------------------------------------------
    # Mode Switching
    # ------------------------------------------------------------------
    def _set_mode(self, mode: str):
        self._mode = mode
        if mode == "object":
            self._mode_label.configure(text="当前：点选对象（双击标记）")
            self._btn_obj_mode.configure(fg_color="#1F6AA5")
            self._btn_area_mode.configure(fg_color=("#3A7EBF", "#1F538D"))
            self._canvas.config(cursor="crosshair")
        else:
            self._mode_label.configure(text="当前：区域框选（拖拽标记）")
            self._btn_obj_mode.configure(fg_color=("#3A7EBF", "#1F538D"))
            self._btn_area_mode.configure(fg_color="#1F6AA5")
            self._canvas.config(cursor="tcross")

        # Cancel any in-progress area drag
        self._area_start = None
        if self._area_rect_id is not None:
            self._canvas.delete(self._area_rect_id)
            self._area_rect_id = None

    # ------------------------------------------------------------------
    # Status bar helpers
    # ------------------------------------------------------------------
    def _set_status(self, text: str):
        self._status_label.configure(text=text)

    # ------------------------------------------------------------------
    # Window close
    # ------------------------------------------------------------------
    def _on_close(self):
        """Save window state and clean up."""
        try:
            geo = self.geometry()
            # Parse "WxH+X+Y"
            import re
            m = re.match(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", geo)
            if m:
                self._config["window"]["width"] = int(m.group(1))
                self._config["window"]["height"] = int(m.group(2))
                self._config["window"]["x"] = int(m.group(3))
                self._config["window"]["y"] = int(m.group(4))
            save_config(self._config)
        except Exception:
            pass

        if self._doc:
            self._doc.close()
        self.destroy()


# =============================================================================
# Entry Point
# =============================================================================
def main():
    """Launch the GUI application."""
    ensure_dirs()

    # Quick check: warn if no PDF files in input/
    files = get_supported_files(INPUT_DIR)
    if not files:
        print("未找到 input 文件夹中的 PDF。")
        pass

    app = PDFViewerApp()

    # Auto-open first file if present
    if files:
        app.after(300, lambda: app._open_pdf(files[0]))

    app.mainloop()


if __name__ == "__main__":
    main()
