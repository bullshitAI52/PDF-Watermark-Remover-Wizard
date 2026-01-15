#!/bin/bash
cd "$(dirname "$0")"

# Define virtual environment directory
VENV_DIR=".venv"

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment... (First run only)"
    python3 -m venv "$VENV_DIR"
fi

# Install dependencies if pikepdf or dashscope is not found
if ! "$VENV_DIR/bin/python" -c "import pikepdf; import dashscope" &> /dev/null; then
    echo "Installing/Updating required libraries..."
    "$VENV_DIR/bin/pip" install -r requirements.txt
fi

echo "========================================"
echo "    PDF Watermark Remover (Mac)"
echo "========================================"
echo " Detected $(ls input/*.pdf 2>/dev/null | wc -l) files in 'input' folder."
echo "========================================"
echo "1. 🚀  One-Click AI Removal (Text Based)"
echo "       - Best for: Normal PDFs with selectable text watermarks."
echo "----------------------------------------"
echo "2. 🪄  Wizard Mode (Interactive)"
echo "       - Best for: When Mode 1 deletes too much."
echo "----------------------------------------"
echo "3. 👁️  Vision AI (Detection Only)"
echo "       - Best for: Finding out WHERE the watermark is."
echo "----------------------------------------"
echo "4. ☁️  AI Inpainting (Universal)"
echo "       - Best for: Images (.jpg/.png) & Complex PDFs."
echo "       - Info: High Quality, Slow, Consumes Credits."
echo "----------------------------------------"
echo "5. ☢️  Nuclear Mode (Vector Killer)"
echo "       - Best for: Stubborn vector paths/shapes. PDF Only."
echo "----------------------------------------"
echo "6. 🖼️  Local Image Mode (Speed)"
echo "       - Best for: Scanned PDFs & Images (.jpg/.png)."
echo "       - Info: Fast, Free, Converts PDF to Image."
echo "========================================"
echo "0. ❌  Exit"
echo "========================================"
read -p "Type 1-6 and press Enter: " choice
choice=${choice:-1} # Default to 1

if [ "$choice" == "1" ]; then
    "$VENV_DIR/bin/python" src/main.py --auto-ai
elif [ "$choice" == "2" ]; then
    "$VENV_DIR/bin/python" src/main.py --wizard
elif [ "$choice" == "3" ]; then
    "$VENV_DIR/bin/python" src/main.py --vision
elif [ "$choice" == "4" ]; then
    "$VENV_DIR/bin/python" image_mode_pic_watermark/raster_cleaner.py --mode 2
elif [ "$choice" == "5" ]; then
    "$VENV_DIR/bin/python" src/vector_killer.py
elif [ "$choice" == "6" ]; then
    "$VENV_DIR/bin/python" image_mode_pic_watermark/raster_cleaner.py --mode 1
else
    echo "Exiting..."
fi

echo ""
echo "Press any key to close..."
read -n 1 -s
