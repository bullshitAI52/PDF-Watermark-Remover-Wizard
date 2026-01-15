---
name: PDF Watermark Remover Wizard
description: A powerful tool to remove stubborn watermarks from PDF files using AI and forensic analysis. Supports text-based, image-based, and vector watermarks.
---

# PDF Watermark Remover Wizard

This skill allows the Agent to remove watermarks from PDF files using a set of specialized scripts.

## Directory Structure
- Root: `/Users/apple/Documents/PDF水印批量删除助手 skill`
- Input Directory: `input/`
- Output Directory: `output/`
- Image Mode Directory: `image_mode_pic_watermark/`

## Usage Instructions

### 1. Standard AI Mode (Recommended for most PDFs)
Best for standard text watermarks or simple logos.

1.  **Place PDF(s)** into the `input/` folder in the root directory.
2.  **Execute** the following command:
    ```bash
    /Users/apple/Documents/PDF水印批量删除助手\ skill/fix_and_run_ai.command
    ```
    *Note: This script automatically handles environment checks and watermark removal.*
3.  **Retrieve** the cleaned PDF from the `output/` folder.

### 2. Universal Killer Mode (For Stubborn Watermarks)
Use this if the Standard AI Mode fails (e.g., watermark changes color, is a shadow, or only partially removed).

1.  **Place PDF(s)** into the `input/` folder.
2.  **Execute** the Python script:
    ```bash
    cd "/Users/apple/Documents/PDF水印批量删除助手 skill"
    python3 universal_killer_v2.py
    ```
3.  **Retrieve** the cleaned PDF from the `output/` folder.

### 3. Image Mode (For Scanned PDFs or Images)
Use this for scanned documents or PDFs where text cannot be selected.

1.  **Navigate** to the image mode directory: `/Users/apple/Documents/PDF水印批量删除助手 skill/image_mode_pic_watermark`.
2.  **Place PDF or Image files** into `image_mode_pic_watermark/input/`.
3.  **Execute** the run command:
    ```bash
    cd "/Users/apple/Documents/PDF水印批量删除助手 skill/image_mode_pic_watermark"
    ./run_image_mode.command
    ```
    *   The script may ask for input (1 for Local, 2 for AI). Use `send_command_input` if interactive, or prefer the standard scripts if automation is needed.*

## Important Notes
- Always check the `output/` folder for results.
- Do not modify the script files unless explicitly requested.
- The `fix_and_run_ai.command` is the safest one-click entry point.
