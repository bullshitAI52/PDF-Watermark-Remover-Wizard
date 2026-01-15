#!/bin/bash
cd "$(dirname "$0")"

# Define virtual environment directory
VENV_DIR=".venv"

echo "============================================="
echo "   🤖 Auto-Pilot Watermark Removal"
echo "   Strategy: Text (1) -> Vector (5) -> Image (6)"
echo "============================================="

# 1. Try Mode 1 (One-Click AI)
echo ""
echo ">>> [Stage 1] Trying One-Click AI (Text)..."
"$VENV_DIR/bin/python" src/main.py --auto-ai

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Success! Watermark removed by Stage 1."
    read -n 1 -s -r -p "Press any key to exit..."
    exit 0
elif [ $EXIT_CODE -eq 10 ]; then
    echo "⚠️ Stage 1 found nothing. Continuing..."
else
    echo "❌ Stage 1 Error. Continuing..."
fi

# 2. Try Mode 5 (Nuclear Mode)
echo ""
echo ">>> [Stage 2] Trying Nuclear Mode (Vectors)..."
"$VENV_DIR/bin/python" src/vector_killer.py --auto

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Success! Watermark removed by Stage 2."
    read -n 1 -s -r -p "Press any key to exit..."
    exit 0
elif [ $EXIT_CODE -eq 10 ]; then
    echo "⚠️ Stage 2 found nothing. Continuing..."
else
    echo "❌ Stage 2 Error. Continuing..."
fi

# 3. Stage 3: Fallback (Image/AI)
if [ "$1" == "--quality" ]; then
    echo ""
    echo ">>> [Stage 3] Trying AI Inpainting (Cloud Ultimate)..."
    echo "ℹ️  Using Alibaba Wanx Model. This will cost API credits."
    "$VENV_DIR/bin/python" image_mode_pic_watermark/raster_cleaner.py --mode 2
else
    echo ""
    echo ">>> [Stage 3] Trying Local Image Mode (Speed Fallback)..."
    echo "ℹ️  Converting to images and cleaning locally (Free/Fast)."
    "$VENV_DIR/bin/python" image_mode_pic_watermark/raster_cleaner.py --mode 1
fi

echo "✅ All Stages Completed. Check 'output' folder."
read -n 1 -s -r -p "Press any key to exit..."
