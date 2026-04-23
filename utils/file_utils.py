# -*- coding: utf-8 -*-
import os
import glob
import shutil
from pathlib import Path

def get_supported_files(directory):
    """Returns a list of supported files in the given directory."""
    patterns = ("*.pdf", "*.jpg", "*.jpeg", "*.png")
    found = []
    for pattern in patterns:
        found.extend(glob.glob(os.path.join(directory, pattern)))
    return sorted(found)

def make_safe_filename(text, max_len=48):
    """Converts a string into a filesystem-safe filename."""
    if text is None:
        return "empty"
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in str(text))
    cleaned = cleaned.strip("_") or "item"
    return cleaned[:max_len]

def ensure_empty_dir(directory):
    """Ensures a directory exists and is empty."""
    if os.path.exists(directory):
        shutil.rmtree(directory)
    os.makedirs(directory, exist_ok=True)

def get_page_preview_name(pdf_name, page_idx, suffix=""):
    """Generates a standard name for a page preview image."""
    base = Path(pdf_name).stem
    return f"preview_{base}_p{page_idx+1}{suffix}.png"
