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
echo "1. 🚀  One-Click AI Removal (No Questions Asked!)"
echo "       - AI automatically finds and deletes watermark"
echo "----------------------------------------"
echo "2. 🪄  Wizard Mode (Ask me to confirm)"
echo "3. 🛠️  Manual Mode (Edit script manually)"
echo "4. ❌  Exit"
echo "========================================"
read -p "Type 1 and press Enter: " choice
choice=${choice:-1} # Default to 1

if [ "$choice" == "1" ]; then
    "$VENV_DIR/bin/python" pdf_watermark_remover.py --auto-ai
elif [ "$choice" == "2" ]; then
    "$VENV_DIR/bin/python" pdf_watermark_remover.py --wizard
elif [ "$choice" == "3" ]; then
    "$VENV_DIR/bin/python" pdf_watermark_remover.py --manual
else
    echo "Exiting..."
fi

echo ""
echo "Press any key to close..."
read -n 1 -s
