#!/bin/bash
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
.venv/bin/python pdf_watermark_remover.py --auto-ai

echo ""
echo "========================================"
echo "Finished. Press any key to close."
read -n 1 -s
