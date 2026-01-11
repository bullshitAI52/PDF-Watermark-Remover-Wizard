# PDF Watermark Removal Assistant (Pro Version)

This tool uses AI and forensic analysis to automatically remove complex watermarks from PDF files.

## 🚀 Quick Start (Recommended)

1.  **Put your PDF files** into the `input` folder.
2.  **Double-click** the `fix_and_run_ai.command` file.
    *   This automatically fixes dependencies and runs the **One-Click AI Removal**.
    *   It detects watermarks intelligently (Text, Tiled Images, etc.).
3.  **Get your files** from the `output` folder.

---

## 🛠️ Operating Modes

### Level 1: One-Click AI (Standard)
*   **Run**: `fix_and_run_ai.command`
*   **Best for**: Most common watermarks (Text, repetitve images).
*   **How it works**: Uses Qwen AI to "look" at the file and decide what to delete.

### Level 2: Interactive Wizard
*   **Run**: `start_mac.command` -> Choose Option 1 ("Wizard")
*   **Best for**: When you want to double-check what the AI found before deleting.
*   **How it works**: Shows you a list of candidates and asks "Is this a watermark? [Y/N]".

### Level 3: The "Universal Killer" (Forensic)
*   **Run**: `python universal_killer_v2.py` (via Terminal)
*   **Best for**: **Extremely stubborn watermarks** that are hidden in layers, shadows, or vector paths (like the "2015" or "Blue/Black" ones).
*   **How it works**: Aggressively targets:
    *   Tiled Background Images (20k+ fragments)
    *   Vector Paths (Blue, Red/Shadow layers)
    *   Invisible Text / Garbled Characters
    *   **Warning**: This mode is very powerful. Check your formulas/diagrams afterwards.

---

## ❓ FAQ

### Q: Do I need to send you screenshots?
**A: Only if Level 1 and Level 2 fail.**

*   **Normal Case**: No. The AI tools (`fix_and_run_ai`) can usually find it blindly.
*   **Tough Case**: If the watermark is still there (or strange colors remain), **YES**, please:
    1.  Provide a **Screenshot** of the watermark.
    2.  Tell me if it "overlaps" text or is underneath.
    3.  I will then write a custom "Killer Script" (like `universal_killer_v2.py`) to target that specific visual pattern.

### Q: Why did the watermark turn black?
**A:** Some watermarks are "Layered". We removed the top (Blue) layer, revealing the bottom (Shadow) layer. Running the **Universal Killer** (`universal_killer_v2.py`) solves this.
