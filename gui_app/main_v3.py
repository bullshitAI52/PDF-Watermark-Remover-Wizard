#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# PDF Watermark Remover Wizard - Visual Pro GUI (V3 Optimized)
# DISCLAIMER: This tool is for PERSONAL STUDY & RESEARCH ONLY.
# STRICTLY PROHIBITED FOR COMMERCIAL USE or ILLEGAL ACTIVITIES.
# -----------------------------------------------------------------------------
"""
V3 optimized visual GUI (parallel to V2 — does not replace main_v2).

Improvements over V2:
- Background-thread whole-book sync (page parsed once for all templates)
- Free-form region marks (area select works even with zero detected objects)
- Grouped per-page export (PyMuPDFEngineV2)
- Cancelable sync, keyboard shortcuts, match mode toggle
"""

from __future__ import annotations

import os
import queue
import re
import sys
import threading
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

import fitz  # PyMuPDF
from PIL import Image, ImageTk

try:
    import customtkinter as ctk
except ImportError:
    print("❌ customtkinter not installed. Run: pip install customtkinter")
    sys.exit(1)

from core.object_engine_v2 import ObjectEngineV2
from core.engine_pymupdf_v2 import PyMuPDFEngineV2
from utils.config_manager import load_config, save_config, ensure_dirs
from utils.file_utils import get_supported_files

# =============================================================================
# Constants
# =============================================================================
APP_TITLE = "PDF 水印清理助手"
DEFAULT_ZOOM = 1.5
MIN_ZOOM = 0.5
MAX_ZOOM = 5.0
ZOOM_STEP = 0.25
CANVAS_MARGIN = 10

COLOR_DETECTED = "#4A90D9"
COLOR_HOVER = "#FF4444"
COLOR_SELECTED = "#FF3333"
COLOR_REGION = "#9B59B6"  # purple — free-form region
COLOR_BOX_SELECT = "#00FF00"

# Softer blue-gray surfaces keep the working area distinct without forcing dark mode.
COLOR_APP_BG = ("#E8EEF5", "#171B22")
COLOR_SIDEBAR_BG = ("#D8E3F0", "#202833")
COLOR_STATUS_BG = ("#F4F7FB", "#202833")
COLOR_CANVAS_BG = "#D7E0EA"

# Default filters: skip drawings for speed (toggleable)
DEFAULT_FILTERS = ["text", "image"]
ALL_FILTERS = ["text", "image", "drawing"]


def scale_bbox(bbox: List[float], zoom: float) -> Tuple[float, float, float, float]:
    return (bbox[0] * zoom, bbox[1] * zoom, bbox[2] * zoom, bbox[3] * zoom)


class PageRenderer:
    """Renders a single PDF page to a PIL Image at a given zoom level."""

    def __init__(self, doc: fitz.Document):
        self._doc = doc
        self._cache: Dict[Tuple[int, float], Image.Image] = {}

    @property
    def page_count(self) -> int:
        return len(self._doc)

    def render(self, page_idx: int, zoom: float = DEFAULT_ZOOM) -> Image.Image:
        key = (page_idx, zoom)
        if key in self._cache:
            return self._cache[key]

        page = self._doc[page_idx]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        if len(self._cache) > 30:
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[key] = img
        return img

    def invalidate(self):
        self._cache.clear()


class PDFViewerAppV3(ctk.CTk):
    """Main Pro V3 GUI — performance-focused interactive watermark removal."""

    def __init__(self):
        super().__init__()

        ensure_dirs()
        self._config = load_config()
        win = self._config.get("window", {})
        theme = self._config.get("theme", {})

        self.title(APP_TITLE)
        self.geometry(f"{win.get('width', 1400)}x{win.get('height', 900)}")
        if win.get("x") and win.get("y"):
            self.geometry(f"+{win['x']}+{win['y']}")
        if win.get("maximized"):
            self.after(100, lambda: self.state("zoomed"))

        ctk.set_appearance_mode(theme.get("mode", "light"))
        ctk.set_default_color_theme(theme.get("color_theme", "blue"))
        self.configure(fg_color=COLOR_APP_BG)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # --- State ---
        self._pdf_path: Optional[str] = None
        self._doc: Optional[fitz.Document] = None
        self._renderer: Optional[PageRenderer] = None
        self._object_engine: Optional[ObjectEngineV2] = None
        self._current_page: int = 0
        self._zoom: float = DEFAULT_ZOOM

        self._tk_image: Any = None
        self._pil_image: Optional[Image.Image] = None
        self._scaled_bboxes: List[Tuple[float, float, float, float]] = []

        self._page_objects: List[Dict] = []
        self._canvas_rects: List[int] = []
        self._marked_objects: List[Dict] = []
        self._marked_all_pages: List[Tuple[int, Dict]] = []
        self._marks_by_page: Dict[int, List[Dict]] = {}

        self._hovered_idx: int = -1
        self._mode: str = "object"  # object | area
        self._area_start: Optional[Tuple[float, float]] = None
        self._area_rect_id: Optional[int] = None

        # Detection / match options
        self._include_drawings = False
        self._match_mode = "loose"  # strict | loose | content
        self._force_free_region = False  # area mode: only paint free rect when checked
        self._overlap_hits: List[int] = []  # indices under cursor (smallest first)
        self._overlap_cycle = 0

        # Sync worker state
        self._sync_busy = False
        self._sync_cancel = threading.Event()
        self._sync_queue: queue.Queue = queue.Queue()
        self._sync_thread: Optional[threading.Thread] = None

        self._build_ui()
        self._bind_shortcuts()
        self._refresh_file_list()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        # Controls exceed a compact window height, so keep the sidebar scrollable.
        # This prevents export and save actions from being clipped below the fold.
        self._sidebar = ctk.CTkScrollableFrame(
            self, width=280, corner_radius=0, fg_color=COLOR_SIDEBAR_BG)
        self._sidebar.grid(row=0, column=0, rowspan=2, sticky="nsw")
        self._build_sidebar()

        self._status = ctk.CTkFrame(self, height=32, corner_radius=0, fg_color=COLOR_STATUS_BG)
        self._status.grid(row=0, column=1, sticky="new")
        self._status.grid_propagate(False)
        self._build_status_bar()

        self._canvas_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._canvas_frame.grid(row=1, column=1, sticky="nsew")
        self._canvas_frame.grid_rowconfigure(0, weight=1)
        self._canvas_frame.grid_columnconfigure(0, weight=1)
        self._build_canvas_area()

    def _build_sidebar(self):
        self._sidebar.grid_columnconfigure(0, weight=1)
        row = 0

        ctk.CTkLabel(
            self._sidebar, text="PDF 去水印",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=row, column=0, padx=12, pady=(16, 4), sticky="w")
        row += 1

        ctk.CTkLabel(
            self._sidebar, text="1 选择文件  →  2 标记水印  →  3 导出结果",
            font=ctk.CTkFont(size=11), text_color="#888888",
        ).grid(row=row, column=0, padx=12, pady=(0, 6), sticky="w")
        row += 1

        ctk.CTkLabel(self._sidebar, text="1 选择 PDF", font=ctk.CTkFont(size=13, weight="bold")) \
            .grid(row=row, column=0, padx=12, pady=(2, 2), sticky="w")
        row += 1
        self._file_listbox = ctk.CTkScrollableFrame(self._sidebar, height=120)
        self._file_listbox.grid(row=row, column=0, padx=8, pady=4, sticky="nsew")
        row += 1

        file_actions = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        file_actions.grid(row=row, column=0, padx=8, pady=(2, 8), sticky="ew")
        file_actions.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(file_actions, text="选择 PDF…", command=self._choose_pdf).grid(row=0, column=0, padx=(0, 3), sticky="ew")
        ctk.CTkButton(file_actions, text="刷新列表", command=self._refresh_file_list).grid(row=0, column=1, padx=(3, 0), sticky="ew")
        row += 1

        ctk.CTkLabel(self._sidebar, text="2 浏览与标记", font=ctk.CTkFont(size=13, weight="bold")) \
            .grid(row=row, column=0, padx=12, pady=(4, 2), sticky="w")
        row += 1
        # Page navigation
        nav_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        nav_frame.grid(row=row, column=0, padx=8, pady=4, sticky="ew")
        nav_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self._btn_prev = ctk.CTkButton(nav_frame, text="◀", width=40, command=self._prev_page)
        self._btn_prev.grid(row=0, column=0, padx=2)
        self._page_label = ctk.CTkLabel(nav_frame, text="第 - / - 页", font=ctk.CTkFont(size=13))
        self._page_label.grid(row=0, column=1)
        self._btn_next = ctk.CTkButton(nav_frame, text="▶", width=40, command=self._next_page)
        self._btn_next.grid(row=0, column=2, padx=2)
        row += 1

        # Zoom
        zoom_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        zoom_frame.grid(row=row, column=0, padx=8, pady=4, sticky="ew")
        zoom_frame.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(zoom_frame, text="−", width=30,
                      command=lambda: self._zoom_in_out(-ZOOM_STEP)).grid(row=0, column=0)
        self._zoom_label = ctk.CTkLabel(zoom_frame, text=f"{self._zoom:.0%}")
        self._zoom_label.grid(row=0, column=1)
        ctk.CTkButton(zoom_frame, text="+", width=30,
                      command=lambda: self._zoom_in_out(ZOOM_STEP)).grid(row=0, column=2)
        row += 1

        # Mode switch
        mode_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        mode_frame.grid(row=row, column=0, padx=8, pady=4, sticky="ew")
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
        row += 1

        ctk.CTkLabel(self._sidebar, text="高级匹配设置", font=ctk.CTkFont(size=11), text_color="#888888") \
            .grid(row=row, column=0, padx=12, pady=(5, 0), sticky="w")
        row += 1
        opt_frame = ctk.CTkFrame(self._sidebar, fg_color=("#F1F5F9", "#30343B"), corner_radius=8)
        opt_frame.grid(row=row, column=0, padx=8, pady=4, sticky="ew")
        self._chk_drawings = ctk.CTkCheckBox(
            opt_frame, text="检测矢量路径 (较慢)",
            command=self._on_filters_changed)
        self._chk_drawings.grid(row=0, column=0, sticky="w")
        self._chk_free_region = ctk.CTkCheckBox(
            opt_frame, text="框选强制自由涂除 (易误伤)",
            command=self._on_free_region_toggled)
        self._chk_free_region.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self._match_label = ctk.CTkLabel(opt_frame, text="匹配模式:", font=ctk.CTkFont(size=11))
        self._match_label.grid(row=2, column=0, sticky="w", pady=(6, 0))
        self._match_menu = ctk.CTkOptionMenu(
            opt_frame,
            values=["宽松 (推荐)", "严格", "仅内容"],
            command=self._on_match_mode_changed,
            width=160,
        )
        self._match_menu.set("宽松 (推荐)")
        self._match_menu.grid(row=3, column=0, sticky="w", pady=(2, 0))
        row += 1

        ctk.CTkLabel(
            self._sidebar, text="3 导出结果",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=row, column=0, padx=12, pady=(10, 2), sticky="w")
        row += 1

        self._btn_save = ctk.CTkButton(
            self._sidebar, text="导出到 output 文件夹",
            height=38, fg_color="#27AE60", hover_color="#219A52",
            font=ctk.CTkFont(size=14, weight="bold"), command=self._quick_save)
        self._btn_save.grid(row=row, column=0, padx=8, pady=(2, 2), sticky="ew")
        row += 1

        self._btn_save_as = ctk.CTkButton(
            self._sidebar, text="💾 另存为…", command=self._save_as)
        self._btn_save_as.grid(row=row, column=0, padx=8, pady=2, sticky="ew")
        row += 1

        # Sync
        self._btn_sync = ctk.CTkButton(
            self._sidebar, text="🌍 全书同步删除",
            fg_color="#E67E22", hover_color="#D35400",
            command=self._sync_all_pages)
        self._btn_sync.grid(row=row, column=0, padx=8, pady=(10, 2), sticky="ew")
        row += 1

        self._btn_cancel_sync = ctk.CTkButton(
            self._sidebar, text="⏹ 取消同步",
            fg_color="#C0392B", hover_color="#A93226",
            command=self._cancel_sync, state="disabled")
        self._btn_cancel_sync.grid(row=row, column=0, padx=8, pady=2, sticky="ew")
        row += 1

        self._btn_clear = ctk.CTkButton(
            self._sidebar, text="🗑️ 清除当前选中",
            fg_color="#95A5A6", hover_color="#7F8C8D",
            command=self._clear_marked)
        self._btn_clear.grid(row=row, column=0, padx=8, pady=2, sticky="ew")
        row += 1

        self._stats_label = ctk.CTkLabel(
            self._sidebar, text="已标记: 0 个对象", font=ctk.CTkFont(size=12))
        self._stats_label.grid(row=row, column=0, padx=8, pady=8)
        row += 1

        tip = (
            "提示：双击对象可标记；重叠时按 Tab 切换。\n"
            "框选默认只标记对象，不会整块涂白。\n"
            "←/→ 翻页；Cmd/Ctrl + S 快速导出。"
        )
        ctk.CTkLabel(
            self._sidebar, text=tip, justify="left",
            font=ctk.CTkFont(size=10), text_color="#888888",
        ).grid(row=row, column=0, padx=10, pady=4, sticky="w")
        row += 1

        self._sidebar.grid_rowconfigure(row, weight=1)

    def _build_canvas_area(self):
        from tkinter import Canvas, Scrollbar, HORIZONTAL, VERTICAL

        self._hbar = Scrollbar(self._canvas_frame, orient=HORIZONTAL)
        self._hbar.grid(row=1, column=0, sticky="ew")
        self._vbar = Scrollbar(self._canvas_frame, orient=VERTICAL)
        self._vbar.grid(row=0, column=1, sticky="ns")

        self._canvas = Canvas(
            self._canvas_frame,
            bg="#2C2C2C" if ctk.get_appearance_mode() == "Dark" else COLOR_CANVAS_BG,
            highlightthickness=0,
            xscrollcommand=self._hbar.set,
            yscrollcommand=self._vbar.set,
            cursor="crosshair",
        )
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._hbar.config(command=self._canvas.xview)
        self._vbar.config(command=self._canvas.yview)

        self._canvas.bind("<Motion>", self._on_mouse_move)
        self._canvas.bind("<Double-Button-1>", self._on_double_click)
        self._canvas.bind("<ButtonPress-1>", self._on_button_press)
        self._canvas.bind("<B1-Motion>", self._on_button_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_button_release)
        self._canvas.bind("<Button-2>", self._on_right_click)
        self._canvas.bind("<Button-3>", self._on_right_click)
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)

        # Drag-and-drop open (Tk 8.6+ / some platforms may not support)
        try:
            self._canvas.drop_target_register("DND_Files")  # type: ignore[attr-defined]
        except Exception:
            pass

        self._placeholder_id = self._canvas.create_text(
            600, 400, text="📂 请选择一个 PDF 文件\n可点“选择 PDF…”或从 input/ 列表打开",
            font=("Helvetica", 18), fill="#888888")
        self._set_mode(self._mode)

    def _build_status_bar(self):
        self._status_label = ctk.CTkLabel(
            self._status, text="准备就绪", anchor="w",
            font=ctk.CTkFont(size=11))
        self._status_label.pack(side="left", padx=12, pady=4)

        self._progress_bar = ctk.CTkProgressBar(self._status, width=150)
        self._progress_bar.set(0)

        self._status_count = ctk.CTkLabel(
            self._status, text="", anchor="e", font=ctk.CTkFont(size=11))
        self._status_count.pack(side="right", padx=12, pady=4)

    def _bind_shortcuts(self):
        self.bind("<Left>", lambda e: self._prev_page())
        self.bind("<Right>", lambda e: self._next_page())
        self.bind("<Command-s>", lambda e: self._quick_save())
        self.bind("<Control-s>", lambda e: self._quick_save())
        self.bind("<Escape>", lambda e: self._cancel_sync())
        self.bind("<plus>", lambda e: self._zoom_in_out(ZOOM_STEP))
        self.bind("<minus>", lambda e: self._zoom_in_out(-ZOOM_STEP))
        self.bind("<equal>", lambda e: self._zoom_in_out(ZOOM_STEP))
        # Cycle overlapping objects under cursor
        self.bind("<Tab>", self._cycle_overlap)
        self.bind("<Shift-Tab>", lambda e: self._cycle_overlap(e, reverse=True))

    # ------------------------------------------------------------------
    # Options
    # ------------------------------------------------------------------
    def _current_filters(self) -> List[str]:
        return ALL_FILTERS if self._include_drawings else DEFAULT_FILTERS

    def _on_filters_changed(self):
        self._include_drawings = bool(self._chk_drawings.get())
        if self._object_engine:
            self._object_engine.invalidate_cache()
        if self._doc:
            self._display_page()

    def _on_match_mode_changed(self, value: str):
        mapping = {
            "严格": "strict",
            "宽松 (推荐)": "loose",
            "仅内容": "content",
        }
        self._match_mode = mapping.get(value, "loose")
        self._set_status(f"匹配模式: {value}")

    def _on_free_region_toggled(self):
        self._force_free_region = bool(self._chk_free_region.get())
        if self._force_free_region:
            self._set_status("⚠️ 已开启强制自由涂除：框选整块会白掉框内所有内容")
        else:
            self._set_status("框选仅标记检测到的对象（无对象时才创建自由区域）")

    # ------------------------------------------------------------------
    # File Management
    # ------------------------------------------------------------------
    def _choose_pdf(self):
        """Open a PDF directly, without requiring users to copy it into input/."""
        from tkinter import filedialog

        path = filedialog.askopenfilename(
            parent=self,
            title="选择要处理的 PDF",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")],
        )
        if path:
            self._open_pdf(path)

    def _refresh_file_list(self):
        for w in self._file_listbox.winfo_children():
            w.destroy()

        files = get_supported_files(INPUT_DIR)
        pdfs = [f for f in files if f.lower().endswith(".pdf")]
        if not pdfs:
            ctk.CTkLabel(
                self._file_listbox,
                text="(没有找到 PDF)\n请将文件放入 input/",
                font=ctk.CTkFont(size=11),
            ).pack(pady=20)
            return

        for fpath in pdfs:
            fname = os.path.basename(fpath)
            btn = ctk.CTkButton(
                self._file_listbox, text=f"📄 {fname}",
                anchor="w", fg_color="transparent", hover_color="#3498DB",
                command=lambda p=fpath: self._open_pdf(p),
            )
            btn.pack(fill="x", padx=2, pady=1)

    def _open_pdf(self, path: str):
        try:
            if self._sync_busy:
                self._cancel_sync()
            if self._doc:
                self._doc.close()

            self._pdf_path = path
            self._doc = fitz.open(path)
            self._renderer = PageRenderer(self._doc)
            self._object_engine = ObjectEngineV2(self._doc)
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
        if not self._doc or not self._renderer or not self._object_engine:
            return

        self._canvas.delete("all")
        self._canvas_rects.clear()
        self._hovered_idx = -1
        self._placeholder_id = None

        self._pil_image = self._renderer.render(self._current_page, self._zoom)
        self._tk_image = ImageTk.PhotoImage(self._pil_image)
        self._photo_refs = getattr(self, "_photo_refs", []) + [self._tk_image]
        if len(self._photo_refs) > 32:
            self._photo_refs = self._photo_refs[-32:]

        self._img_canvas_id = self._canvas.create_image(
            CANVAS_MARGIN, CANVAS_MARGIN, anchor="nw", image=self._tk_image
        )

        w, h = self._pil_image.width, self._pil_image.height
        self._canvas.config(scrollregion=(0, 0, w + 20, h + 20))

        self._page_objects = self._object_engine.get_page_objects(
            self._current_page, filters=self._current_filters()
        )

        self._scaled_bboxes = []
        m = CANVAS_MARGIN
        for i, obj in enumerate(self._page_objects):
            sx0, sy0, sx1, sy1 = scale_bbox(obj["bbox"], self._zoom)
            sx0 += m
            sy0 += m
            sx1 += m
            sy1 += m
            rid = self._canvas.create_rectangle(
                sx0, sy0, sx1, sy1,
                outline=COLOR_DETECTED, width=1, tags=f"obj_{i}"
            )
            self._canvas_rects.append(rid)
            self._scaled_bboxes.append((sx0, sy0, sx1, sy1))

        self._redraw_marked()

        self._page_label.configure(
            text=f"第 {self._current_page + 1} / {self._doc.page_count} 页")
        total_marked = self._count_all_marks()
        self._stats_label.configure(text=f"已标记: {total_marked} 处")
        self._status_count.configure(text=f"检测到 {len(self._page_objects)} 个对象")

    def _redraw_marked(self):
        self._canvas.delete("marked")
        for page_idx, mobj in self._marked_all_pages:
            if page_idx == self._current_page:
                self._highlight_marked_on_canvas(mobj)
        for mobj in self._marked_objects:
            self._highlight_marked_on_canvas(mobj)

    def _highlight_marked_on_canvas(self, obj: Dict):
        sx0, sy0, sx1, sy1 = scale_bbox(obj["bbox"], self._zoom)
        m = CANVAS_MARGIN
        color = COLOR_REGION if obj.get("type") == "region" else COLOR_SELECTED
        self._canvas.create_rectangle(
            sx0 + m, sy0 + m, sx1 + m, sy1 + m,
            fill=color, outline=color, width=1, stipple="gray25",
            tags="marked",
        )

    # ------------------------------------------------------------------
    # Interaction Handlers
    # ------------------------------------------------------------------
    @staticmethod
    def _bbox_area(bbox: Tuple[float, float, float, float]) -> float:
        return max(1.0, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))

    def _page_area_pdf(self) -> float:
        if not self._doc or self._current_page >= self._doc.page_count:
            return 1.0
        r = self._doc[self._current_page].rect
        return max(float(r.width * r.height), 1.0)

    def _is_fullpage_like(self, obj: Dict, bbox_canvas: Optional[Tuple[float, float, float, float]] = None) -> bool:
        """True for near-full-page images / frames (usually body scan, not watermark)."""
        b = obj.get("bbox") or [0, 0, 0, 0]
        area = max(0.0, (b[2] - b[0]) * (b[3] - b[1]))
        ratio = area / self._page_area_pdf()
        if obj.get("type") == "image" and ratio >= 0.45:
            return True
        if obj.get("type") == "drawing" and ratio >= 0.55:
            return True
        return False

    @staticmethod
    def _looks_like_watermark_text(obj: Dict) -> bool:
        """Heuristic boost for typical ad/contact stamp text."""
        if obj.get("type") != "text":
            return False
        t = str(obj.get("text") or "")
        keys = (
            "微信", "wx", "QQ", "qq", "http", "www.", ".com", ".cn",
            "扫码", "关注", "资料", "添加", "客服", "公众号", "抖音",
            "淘宝", "拼多多", "复制", "链接", "下载",
        )
        low = t.casefold()
        if any(k.casefold() in low for k in keys):
            return True
        # small stamp near edges often watermark
        size = float(obj.get("size") or 0)
        if size and size <= 14 and len(t.strip()) >= 6:
            return True
        return False

    def _hit_score(self, i: int, bbox: Tuple[float, float, float, float]) -> Tuple:
        """Lower score = better (preferred) pick under cursor."""
        obj = self._page_objects[i] if i < len(self._page_objects) else {}
        otype = obj.get("type", "")
        area = self._bbox_area(bbox)
        page_area_canvas = self._page_area_pdf() * (self._zoom ** 2)
        ratio = area / max(page_area_canvas, 1.0)

        # type base rank
        type_rank = {"text": 0, "image": 2, "drawing": 3, "region": 4}.get(otype, 5)

        # Full-page scan image must almost never win the click
        fullpage_penalty = 0
        if self._is_fullpage_like(obj):
            fullpage_penalty = 10**12
            type_rank = 9

        # Prefer smaller boxes; slight preference for smaller font text (stamps)
        font_penalty = 0.0
        if otype == "text":
            size = float(obj.get("size") or 12)
            # large title text (e.g. 26pt 阅读理解…) ranks worse than 12pt stamp
            font_penalty = size * 80.0
            if self._looks_like_watermark_text(obj):
                font_penalty -= 500.0  # boost

        # Huge coverage penalty even if not "full page"
        if ratio >= 0.35:
            fullpage_penalty += 10**9 * ratio

        return (fullpage_penalty, area + font_penalty, type_rank, i)

    def _hit_test(self, mx: float, my: float) -> Tuple[int, List[int]]:
        """Return best object index under cursor + all hits sorted by precision.

        When watermarks / content boxes overlap:
        - prefer smallest stamp text over large titles
        - deprioritize / bury near-full-page images (body scans)
        """
        scored: List[Tuple] = []
        for i, bbox in enumerate(self._scaled_bboxes):
            if bbox[0] <= mx <= bbox[2] and bbox[1] <= my <= bbox[3]:
                scored.append(self._hit_score(i, bbox))
        if not scored:
            return -1, []
        scored.sort()
        ordered = [s[-1] for s in scored]
        # Default pick: first non-fullpage if any
        best = ordered[0]
        for i in ordered:
            obj = self._page_objects[i]
            if not self._is_fullpage_like(obj):
                best = i
                break
        # Reorder list: non-fullpage first (keep relative score order), fullpage last
        primary = [i for i in ordered if not self._is_fullpage_like(self._page_objects[i])]
        buried = [i for i in ordered if self._is_fullpage_like(self._page_objects[i])]
        ordered = primary + buried
        if best not in ordered and ordered:
            best = ordered[0]
        return best, ordered

    def _apply_hover(self, found_idx: int):
        if found_idx == self._hovered_idx:
            return
        if 0 <= self._hovered_idx < len(self._canvas_rects):
            self._canvas.itemconfig(
                self._canvas_rects[self._hovered_idx],
                outline=COLOR_DETECTED, width=1)
        self._hovered_idx = found_idx
        if 0 <= found_idx < len(self._canvas_rects):
            self._canvas.itemconfig(
                self._canvas_rects[found_idx],
                outline=COLOR_HOVER, width=2)
            obj = self._page_objects[found_idx]
            snippet = str(obj.get("text") or "")[:40]
            n_overlap = len(self._overlap_hits)
            extra = f"  [重叠{n_overlap}个 Tab切换]" if n_overlap > 1 else ""
            self._status_count.configure(
                text=f"悬停: {obj.get('type', '?')} \"{snippet}\"{extra}"
            )

    def _cycle_overlap(self, event=None, reverse: bool = False):
        """Tab: cycle among stacked objects under last hover point."""
        if not self._overlap_hits:
            return "break"
        if reverse:
            self._overlap_cycle = (self._overlap_cycle - 1) % len(self._overlap_hits)
        else:
            self._overlap_cycle = (self._overlap_cycle + 1) % len(self._overlap_hits)
        idx = self._overlap_hits[self._overlap_cycle]
        self._apply_hover(idx)
        obj = self._page_objects[idx]
        snippet = str(obj.get("text") or "")[:40]
        self._set_status(
            f"重叠切换 {self._overlap_cycle + 1}/{len(self._overlap_hits)}: "
            f"{obj.get('type')} \"{snippet}\""
        )
        return "break"

    def _on_mouse_move(self, event):
        if not self._page_objects or not self._scaled_bboxes:
            return
        if self._area_start is not None:
            return

        mx, my = self._canvas.canvasx(event.x), self._canvas.canvasy(event.y)
        found_idx, hits = self._hit_test(mx, my)
        # Keep cycle index if still on same stack set
        if hits != self._overlap_hits:
            self._overlap_hits = hits
            self._overlap_cycle = 0
            if hits:
                found_idx = hits[0]
        elif hits:
            # stick to user-cycled choice while mouse stays in stack
            found_idx = hits[self._overlap_cycle % len(hits)]

        self._apply_hover(found_idx)

    def _on_double_click(self, event):
        if not self._page_objects or self._hovered_idx < 0:
            return
        if self._hovered_idx >= len(self._page_objects):
            return
        # Re-hit at click point so we always use the most precise object
        mx, my = self._canvas.canvasx(event.x), self._canvas.canvasy(event.y)
        best, hits = self._hit_test(mx, my)
        if hits:
            self._overlap_hits = hits
            if self._hovered_idx in hits:
                best = self._hovered_idx  # honor Tab selection
            else:
                best = hits[0]
        if best < 0:
            return
        self._mark_object(self._page_objects[best])

    def _on_button_press(self, event):
        if self._mode != "area":
            return
        self._area_start = (self._canvas.canvasx(event.x), self._canvas.canvasy(event.y))

    def _on_button_drag(self, event):
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

    def _object_fits_selection(
        self,
        sbbox: Tuple[float, float, float, float],
        rx0: float, ry0: float, rx1: float, ry1: float,
    ) -> bool:
        """Avoid grabbing a huge intersecting frame when boxing a small watermark.

        Accept if:
        - object is mostly inside the selection, or
        - center is inside AND object is not much larger than the selection.
        """
        ox0, oy0, ox1, oy1 = sbbox
        # Intersection
        ix0, iy0 = max(ox0, rx0), max(oy0, ry0)
        ix1, iy1 = min(ox1, rx1), min(oy1, ry1)
        if ix1 <= ix0 or iy1 <= iy0:
            return False
        inter = (ix1 - ix0) * (iy1 - iy0)
        obj_area = self._bbox_area(sbbox)
        sel_area = max(1.0, (rx1 - rx0) * (ry1 - ry0))
        coverage = inter / obj_area
        cx = (ox0 + ox1) / 2
        cy = (oy0 + oy1) / 2
        center_in = rx0 <= cx <= rx1 and ry0 <= cy <= ry1

        if coverage >= 0.65:
            return True
        if center_in and obj_area <= sel_area * 1.8:
            return True
        # fully contained
        if ox0 >= rx0 and oy0 >= ry0 and ox1 <= rx1 and oy1 <= ry1:
            return True
        return False

    def _on_button_release(self, event):
        if self._mode != "area" or self._area_start is None:
            return

        sx, sy = self._area_start
        ex, ey = self._canvas.canvasx(event.x), self._canvas.canvasy(event.y)
        rx0, ry0 = min(sx, ex), min(sy, ey)
        rx1, ry1 = max(sx, ex), max(sy, ey)

        # Too small → ignore (accidental click)
        if abs(rx1 - rx0) < 4 or abs(ry1 - ry0) < 4:
            if self._area_rect_id is not None:
                self._canvas.delete(self._area_rect_id)
            self._area_rect_id = None
            self._area_start = None
            return

        marked_count = 0
        for i, obj in enumerate(self._page_objects):
            if i >= len(self._scaled_bboxes):
                continue
            sbbox = self._scaled_bboxes[i]
            if self._object_fits_selection(sbbox, rx0, ry0, rx1, ry1):
                self._mark_object(obj)
                marked_count += 1

        # Free-form region: only when forced, or when no objects were caught
        # (prevents whole-rect wipe that deletes non-watermark content in the box)
        m = CANVAS_MARGIN
        pdf_bbox = [
            (rx0 - m) / self._zoom,
            (ry0 - m) / self._zoom,
            (rx1 - m) / self._zoom,
            (ry1 - m) / self._zoom,
        ]
        added_region = False
        if self._force_free_region or marked_count == 0:
            region_obj = {"type": "region", "bbox": pdf_bbox, "text": ""}
            self._mark_object(region_obj)
            marked_count += 1
            added_region = True

        if added_region and marked_count == 1:
            self._set_status(
                f"区域框选: 自由涂除 "
                f"{pdf_bbox[2]-pdf_bbox[0]:.0f}×{pdf_bbox[3]-pdf_bbox[1]:.0f} "
                f"(框内无独立对象)"
            )
        elif added_region:
            self._set_status(
                f"区域框选: 标记 {marked_count} 处 (含强制自由涂除，注意误伤)"
            )
        else:
            self._set_status(
                f"区域框选: 仅标记 {marked_count} 个对象 (未整块涂白，避免误删正文)"
            )

        if self._area_rect_id is not None:
            self._canvas.delete(self._area_rect_id)
            self._area_rect_id = None
        self._area_start = None

    def _on_right_click(self, event):
        from tkinter import Menu

        # Refresh hit list at click point
        mx, my = self._canvas.canvasx(event.x), self._canvas.canvasy(event.y)
        best, hits = self._hit_test(mx, my)
        if hits:
            self._overlap_hits = hits
            self._overlap_cycle = 0
            self._apply_hover(best)

        menu = Menu(self, tearoff=0)
        if hits:
            # Prefer showing current hover first in the list
            show = list(hits)
            if self._hovered_idx in show:
                show.remove(self._hovered_idx)
                show.insert(0, self._hovered_idx)
            for rank, idx in enumerate(show[:10]):
                obj = self._page_objects[idx]
                snippet = str(obj.get("text") or "")[:22] or f"#{idx}"
                otype = obj.get("type", "?")
                if self._is_fullpage_like(obj):
                    label = f"{'✓ ' if idx == self._hovered_idx else '  '}⚠ 全页图片(正文勿删)"
                elif self._looks_like_watermark_text(obj):
                    label = f"{'✓ ' if idx == self._hovered_idx else '  '}💧 水印候选: {snippet}"
                elif otype == "text" and float(obj.get("size") or 0) >= 18:
                    label = f"{'✓ ' if idx == self._hovered_idx else '  '}📄 标题/正文: {snippet}"
                else:
                    label = f"{'✓ ' if idx == self._hovered_idx else '  '}{otype}: {snippet}"
                menu.add_command(
                    label=label,
                    command=lambda o=obj: self._mark_object(o))
            if len(hits) > 1:
                menu.add_separator()
                menu.add_command(
                    label=f"重叠 {len(hits)} 个 — Tab 切换 · 只删带💧的",
                    state="disabled")
        else:
            menu.add_command(label="(无对象)", state="disabled")

        menu.add_separator()
        menu.add_command(label="🌍 全书同步删除", command=self._sync_all_pages)
        menu.add_command(label="⏹ 取消同步", command=self._cancel_sync)
        menu.add_separator()
        menu.add_command(label="🗑️ 清除所有标记", command=self._clear_marked)
        menu.add_command(label="📄 重置当前页", command=self._display_page)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _on_mousewheel(self, event):
        # macOS uses event.delta differently; support both
        delta = event.delta
        if sys.platform == "darwin":
            self._canvas.yview_scroll(int(-1 * delta), "units")
        else:
            self._canvas.yview_scroll(int(-1 * (delta / 120)), "units")

    # ------------------------------------------------------------------
    # Object Marking
    # ------------------------------------------------------------------
    def _mark_object(self, obj: Dict):
        obj_key = self._obj_key(obj)

        for i, existing in enumerate(self._marked_objects):
            if self._obj_key(existing) == obj_key:
                del self._marked_objects[i]
                self._redraw_marked()
                total = self._count_all_marks()
                self._stats_label.configure(text=f"已标记: {total} 处")
                self._set_status(f"已取消标记: {obj.get('type', '?')}")
                return

        # Block / warn dangerous marks (full-page scan image = almost always body)
        warn = ""
        if self._is_fullpage_like(obj):
            self._set_status(
                "⛔ 已拦截：这是全页扫描图/大底图，删除会抹掉整页正文。"
                "请改选上方小字水印（如「微信/更多资料」）。"
            )
            return

        try:
            b = obj.get("bbox") or [0, 0, 0, 0]
            area = max(0.0, (b[2] - b[0]) * (b[3] - b[1]))
            page_area = self._page_area_pdf()
            ratio = area / page_area
            if obj.get("type") == "text" and float(obj.get("size") or 0) >= 18:
                if not self._looks_like_watermark_text(obj):
                    warn = " ⚠️ 像标题/正文大字，确认不是水印再同步"
            elif ratio >= 0.25 and obj.get("type") != "region":
                warn = f" ⚠️ 框很大({ratio:.0%}页)，可能误伤正文"
            elif ratio >= 0.12 and obj.get("type") == "drawing":
                warn = f" ⚠️ 大矢量框({ratio:.0%}页)，确认是否只要内层水印"
            if self._looks_like_watermark_text(obj):
                warn = " 💧 水印候选" + warn
        except Exception:
            pass

        self._marked_objects.append(obj)
        self._highlight_marked_on_canvas(obj)

        total = self._count_all_marks()
        self._stats_label.configure(text=f"已标记: {total} 处")
        snippet = str(obj.get("text", "") or "")[:30]
        self._set_status(
            f"已标记: {obj.get('type', '?')} \"{snippet}\" "
            f"@ ({obj['bbox'][0]:.1f}, {obj['bbox'][1]:.1f}){warn}"
        )

    def _obj_key(self, obj: Dict) -> str:
        return ObjectEngineV2.obj_key(None, obj)

    def _count_all_marks(self) -> int:
        self._marks_by_page[self._current_page] = list(self._marked_objects)
        page_marks = sum(len(marks) for marks in self._marks_by_page.values())
        return page_marks + len(self._marked_all_pages)

    def _clear_marked(self):
        count = self._count_all_marks()
        self._marked_objects.clear()
        self._marked_all_pages.clear()
        self._marks_by_page.clear()
        self._canvas.delete("marked")
        self._set_status(f"已清除 {count} 个标记")
        self._stats_label.configure(text="已标记: 0 处")

    # ------------------------------------------------------------------
    # Whole-book sync (background thread)
    # ------------------------------------------------------------------
    def _sync_all_pages(self):
        if self._sync_busy:
            self._set_status("⚠️ 同步进行中，可点「取消同步」。")
            return

        self._marks_by_page[self._current_page] = list(self._marked_objects)
        all_templates: List[Dict] = []
        for marks in self._marks_by_page.values():
            all_templates.extend(marks)
        # Also include already-synced as extra templates? No — only user marks.
        # Exclude pure free-form regions from auto-match (no content fingerprint)
        templates = [t for t in all_templates if t.get("type") != "region"]

        if not self._object_engine or not templates:
            if all_templates and not templates:
                self._set_status(
                    "⚠️ 自由区域不会自动全书匹配；请标记文字/图片/矢量对象后再同步。"
                )
            else:
                self._set_status("⚠️ 请先标记至少一个水印对象（非纯区域）。")
            return

        total_pages = self._doc.page_count if self._doc else 0
        pdf_path = self._pdf_path
        self._sync_busy = True
        self._sync_cancel.clear()
        self._btn_sync.configure(state="disabled")
        self._btn_cancel_sync.configure(state="normal")
        self._progress_bar.pack(side="left", padx=10)
        self._progress_bar.set(0)
        self._set_status(f"⏳ 全书同步中 (后台) 0/{total_pages}…")
        self.update_idletasks()

        # Worker opens its own fitz.Document to avoid UI/thread contention.
        templates_snap = list(templates)
        mode = self._match_mode
        filters = self._current_filters()
        q = self._sync_queue
        cancel = self._sync_cancel

        def worker():
            worker_doc = None
            try:
                worker_doc = fitz.open(pdf_path)
                engine = ObjectEngineV2(worker_doc)

                def progress(done, total, msg):
                    if cancel.is_set():
                        return
                    q.put(("progress", done, total, msg))

                results = engine.find_matches_batch(
                    templates_snap,
                    range(total_pages),
                    mode=mode,
                    filters=filters,
                    progress_cb=progress,
                    cancel_flag=cancel.is_set,
                )
                if cancel.is_set():
                    q.put(("cancelled",))
                else:
                    q.put(("done", results))
            except Exception as exc:
                q.put(("error", str(exc), traceback.format_exc()))
            finally:
                if worker_doc is not None:
                    try:
                        worker_doc.close()
                    except Exception:
                        pass

        self._sync_thread = threading.Thread(target=worker, daemon=True)
        self._sync_thread.start()
        self.after(80, self._sync_poll)

    def _sync_poll(self):
        try:
            while True:
                msg = self._sync_queue.get_nowait()
                kind = msg[0]
                if kind == "progress":
                    _, done, total, text = msg
                    if total > 0:
                        self._progress_bar.set(done / total)
                    self._set_status(f"⏳ 全书同步中 ({done}/{total}) {text}")
                elif kind == "done":
                    results = msg[1]
                    self._sync_finish(results)
                    return
                elif kind == "cancelled":
                    self._sync_cleanup()
                    self._set_status("⏹ 同步已取消")
                    return
                elif kind == "error":
                    self._sync_cleanup()
                    self._set_status(f"❌ 同步出错: {msg[1]}")
                    print(msg[2] if len(msg) > 2 else msg[1])
                    return
        except queue.Empty:
            pass

        if self._sync_busy:
            self.after(80, self._sync_poll)

    def _sync_finish(self, results: List[Tuple[int, Dict]]):
        # Dedup against existing marks
        existing = set()
        for p, o in self._marked_all_pages:
            existing.add(ObjectEngineV2.obj_key(p, o))
        for p, marks in self._marks_by_page.items():
            for o in marks:
                existing.add(ObjectEngineV2.obj_key(p, o))

        new_items = []
        for page_idx, obj in results:
            k = ObjectEngineV2.obj_key(page_idx, obj)
            if k not in existing:
                existing.add(k)
                new_items.append((page_idx, obj))

        self._marked_all_pages.extend(new_items)
        total = self._count_all_marks()
        self._stats_label.configure(text=f"已标记: {total} 处 (含全书同步)")
        self._set_status(
            f"🌍 全书同步完成: 新匹配 {len(new_items)} 处，共 {total} 处"
        )
        self._sync_cleanup()
        self._display_page()

    def _sync_cleanup(self):
        self._progress_bar.pack_forget()
        self._btn_sync.configure(state="normal")
        self._btn_cancel_sync.configure(state="disabled")
        self._sync_busy = False
        self._sync_thread = None

    def _cancel_sync(self):
        if not self._sync_busy:
            return
        self._sync_cancel.set()
        self._set_status("⏹ 正在取消同步…")

    # ------------------------------------------------------------------
    # Save / Export
    # ------------------------------------------------------------------
    def _collect_all_removals(self) -> List[Tuple[int, Dict]]:
        self._marks_by_page[self._current_page] = list(self._marked_objects)
        all_items: List[Tuple[int, Dict]] = []

        for p_idx, marks in self._marks_by_page.items():
            for obj in marks:
                all_items.append((p_idx, obj))
        all_items.extend(self._marked_all_pages)

        seen = set()
        unique = []
        for page_idx, obj in all_items:
            k = ObjectEngineV2.obj_key(page_idx, obj)
            if k not in seen:
                seen.add(k)
                unique.append((page_idx, obj))
        return unique

    def _quick_save(self):
        if not self._pdf_path or not self._doc:
            self._set_status("⚠️ 请先打开一个 PDF 文件。")
            return
        removals = self._collect_all_removals()
        if not removals:
            self._set_status("⚠️ 没有标记任何对象，请先标记水印。")
            return
        base = Path(self._pdf_path).stem
        out_path = os.path.join(OUTPUT_DIR, f"{base}_cleaned_v3.pdf")
        self._do_save(out_path)

    def _save_as(self):
        if not self._pdf_path or not self._doc:
            self._set_status("⚠️ 请先打开一个 PDF 文件。")
            return
        removals = self._collect_all_removals()
        if not removals:
            self._set_status("⚠️ 没有标记任何对象，请先标记水印。")
            return

        from tkinter import filedialog
        out_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialdir=OUTPUT_DIR,
            initialfile=f"{Path(self._pdf_path).stem}_cleaned_v3.pdf",
        )
        if out_path:
            self._do_save(out_path)

    def _do_save(self, out_path: str):
        removals = self._collect_all_removals()
        if not removals:
            return

        self._set_status("⏳ 正在处理并保存，请稍候…")
        self.update_idletasks()

        try:
            engine = PyMuPDFEngineV2(self._pdf_path)
            n = engine.remove_objects(removals, out_path)
            engine.close()
            self._set_status(f"✅ 保存成功 (清除 {n} 处) → {os.path.basename(out_path)}")
            # Reveal in Finder on macOS
            if sys.platform == "darwin" and os.path.exists(out_path):
                try:
                    import subprocess
                    subprocess.run(["open", "-R", out_path], check=False)
                except Exception:
                    pass
        except Exception as exc:
            self._set_status(f"❌ 保存失败: {exc}")
            traceback.print_exc()

    # ------------------------------------------------------------------
    # Navigation & Zoom
    # ------------------------------------------------------------------
    def _prev_page(self):
        if not self._doc or self._current_page <= 0:
            return
        self._marks_by_page[self._current_page] = list(self._marked_objects)
        self._current_page -= 1
        self._marked_objects = list(self._marks_by_page.get(self._current_page, []))
        self._display_page()

    def _next_page(self):
        if not self._doc or self._current_page >= self._doc.page_count - 1:
            return
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
        self._area_start = None
        if self._area_rect_id is not None:
            self._canvas.delete(self._area_rect_id)
            self._area_rect_id = None

    def _set_status(self, text: str):
        self._status_label.configure(text=text)

    def _on_close(self):
        try:
            if self._sync_busy:
                self._sync_cancel.set()
            geo = self.geometry()
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


def main():
    ensure_dirs()
    files = [f for f in get_supported_files(INPUT_DIR) if f.lower().endswith(".pdf")]
    app = PDFViewerAppV3()
    if files:
        app.after(300, lambda: app._open_pdf(files[0]))
    app.mainloop()


if __name__ == "__main__":
    main()
