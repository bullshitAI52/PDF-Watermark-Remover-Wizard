#!/bin/bash
cd "$(dirname "$0")"

echo "========================================================"
echo "          PDF Watermark Assistant - API Setup           "
echo "========================================================"

KEY_FILE=".qwen_key"

if [ -f "$KEY_FILE" ]; then
    CURRENT_KEY=$(cat "$KEY_FILE")
    echo "✅ API Key is currently set."
    echo "Key: ${CURRENT_KEY:0:5}......${CURRENT_KEY: -5}"
    echo ""
    read -p "Do you want to change/update it? (y/n): " choice
    if [[ "$choice" != "y" && "$choice" != "Y" ]]; then
        echo "Exiting..."
        exit 0
    fi
fi

echo ""
echo "Please enter your Dashscope (Qwen) API Key:"
echo "(You can get one from: https://bailian.console.aliyun.com/)"
read -p "Key: " NEW_KEY

if [ -n "$NEW_KEY" ]; then
    echo "$NEW_KEY" > "$KEY_FILE"
    echo ""
    echo "✅ Success! API Key saved to '$KEY_FILE'"
else
    echo "❌ No key entered. Exiting."
fi

read -p "Press Enter to close..."
