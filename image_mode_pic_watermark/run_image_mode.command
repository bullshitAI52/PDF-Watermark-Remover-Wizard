#!/bin/bash

# -----------------------------------------------------------------------------
# DISCLAIMER: PERSONAL STUDY & RESEARCH ONLY. NO COMMERCIAL USE.
# 免责声明：仅供个人学习，严禁商用。
# -----------------------------------------------------------------------------
cd "$(dirname "$0")"

echo "========================================================"
echo "      PDF Image Watermark Cleaner (Vision AI)           "
echo "========================================================"
echo "This mode converts PDF -> Images -> AI Clean -> PDF"
echo "It works for 'Flattened' PDFs where text cannot be selected."
echo "--------------------------------------------------------"

# Ensure venv
if [ ! -d "../.venv" ]; then
    echo "Virtual environment not found! Please run 'fix_and_run_ai.command' in the parent folder first."
    exit 1
fi

# Run
../.venv/bin/python raster_cleaner.py

echo "========================================================"
echo "Done! Check the 'output' folder."
read -p "Press Enter to exit..."
