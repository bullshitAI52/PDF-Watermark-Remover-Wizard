---
name: PDF Watermark Remover Wizard
description: A powerful tool to remove stubborn watermarks from PDF files using AI and forensic analysis. Supports text-based, image-based, and vector watermarks.
---

# PDF Watermark Remover Wizard

This skill allows the Agent to remove watermarks from PDF files using a set of specialized scripts.

## Directory Structure
- `core/`: Unified PDF processing engines.
- `gui_app/`: Modern Desktop GUI interface.
- `web/`: Interactive Web Wizard interface.
- `utils/`: Shared configuration and file helpers.
- `tools/`: Advanced forensic and debugging scripts.
- `input/`: Place your PDFs here.
- `output/`: Cleaned PDFs will appear here.

## Usage Instructions

### Main Entry Point
The unified entry point for all modes on Mac:
```bash
./start_mac.command
```

### Modes Explanation
1.  **Auto-Heuristic (Mode 1)**: Fast removal for standard repeating watermarks.
2.  **Wizard Mode (Mode 2)**: Step-by-step confirmation of detected patterns.
3.  **Vision AI (Mode 3)**: Uses Visual LLM to detect watermarks.
4.  **AI Inpainting (Mode 4)**: Image-level watermark removal.
5.  **Nuclear Mode (Mode 5)**: Strips vector paths and shapes.
6.  **Local Image Mode (Mode 6)**: Fast, free local CV2 cleaning.
7.  **Web Wizard (Mode 8)**: Modern interactive web interface.
8.  **GUI Tool (Mode 9)**: Standalone desktop application.

## Important Notes
- Always check the `output/` folder for results.
- If `start_mac.command` fails due to permissions, run `chmod +x *.command` first.

## Advanced Technique: Removing Image-Based PDF Watermarks (White Box Masking)

When dealing with scanned PDFs where the entire page content is rasterized into a single image (e.g., a 1587x2245 `Image XObject`), watermarks like headers or footers are often baked directly into this background image. Standard text-matching operators (`Tj` / `TJ`) will fail to detect them, such as stubborn promotional text like "【厦门郭老师学习交流群 】" or "一 帮助更多家长获取厦门学习资源 —".

### The Problem
- The watermark text is not a text layer; it is part of the image.
- Deleting the `Image XObject` would remove the entire page's legitimate content.

### The Solution: White Box Masking
Instead of deleting the image, we cover the baked-in watermarks by drawing white rectangles over them using PDF content stream operations. Since these watermarks typically appear at fixed positions (e.g., top headers and bottom footers), we can append drawing commands to the end of `page.Contents`.

**Example Implementation:**
```python
import pikepdf

# Open the PDF allowing in-place edits
pdf = pikepdf.open('input.pdf', allow_overwriting_input=True)

for page in pdf.pages:
    # PDF graphics operators:
    # `q`          : Save graphics state
    # `1 1 1 rg`   : Set fill color to RGB white
    # `x y w h re` : Define a rectangle path
    # `f`          : Fill the path
    # `Q`          : Restore graphics state
    #
    # Example below covers the header (Y > 790) and the footer (Y < 35)
    cover_cmds = b'\nq\n1 1 1 rg\n0 790 1000 1000 re\nf\n0 0 1000 35 re\nf\nQ\n'
    new_stream = pdf.make_stream(cover_cmds)
    
    if isinstance(page.Contents, pikepdf.Array):
        page.Contents.append(new_stream)
    else:
        page.Contents = pikepdf.Array([page.Contents, new_stream])

pdf.save('output.pdf')
```
This completely hides the baked-in text watermarks without breaking the layout or deleting the underlying scanned content.
