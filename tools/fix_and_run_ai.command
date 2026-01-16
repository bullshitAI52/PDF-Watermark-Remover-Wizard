#!/bin/bash

# -----------------------------------------------------------------------------
# DISCLAIMER: PERSONAL STUDY & RESEARCH ONLY. NO COMMERCIAL USE.
# 免责声明：仅供个人学习，严禁商用。
# -----------------------------------------------------------------------------
cd "$(dirname "$0")"

echo "========================================"
echo "      Auto-Repair & Run AI Mode"
echo "========================================"
echo "1. Checking environment..."

VENV_DIR="../.venv"

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

echo "2. Re-installing AI libraries (fixing missing Dashscope)..."
"$VENV_DIR/bin/pip" install pikepdf dashscope

echo "3. Starting One-Click AI Removal..."
echo "----------------------------------------"
"$VENV_DIR/bin/python" ../src/main.py --auto-ai

echo ""
echo "========================================"
echo "Finished. Press any key to close."
read -n 1 -s
