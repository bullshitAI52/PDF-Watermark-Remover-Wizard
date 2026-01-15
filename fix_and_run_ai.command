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

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

echo "2. Re-installing AI libraries (fixing missing Dashscope)..."
.venv/bin/pip install pikepdf dashscope

echo "3. Starting One-Click AI Removal..."
echo "----------------------------------------"
.venv/bin/python src/main.py --auto-ai

echo ""
echo "========================================"
echo "Finished. Press any key to close."
read -n 1 -s
