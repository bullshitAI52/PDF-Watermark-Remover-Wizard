#!/bin/bash
cd "$(dirname "$0")"

echo "========================================================"
echo "          PDF Watermark Assistant - Web UI              "
echo "========================================================"
echo "Starting local server..."

# Ensure venv
if [ ! -d ".venv" ]; then
    echo "Virtual environment not verified. Please run 'fix_and_run_ai.command' first."
    exit 1
fi

# Run Streamlit
.venv/bin/streamlit run app.py
