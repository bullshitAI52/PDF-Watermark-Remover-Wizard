#!/bin/bash

# 获取脚本所在目录
cd "$(dirname "$0")"

# 定义虚拟环境目录
VENV_DIR=".venv"

echo "========================================"
echo "    PDF 水印批量删除助手 (一键启动)"
echo "========================================"
echo ""

# 1. 检查 Python 3 是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未检测到 python3，请先安装 Python！"
    echo "访问: https://www.python.org/downloads/"
    exit 1
fi

# 2. 创建并配置虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 正在创建虚拟环境 (仅限首次运行)..."
    python3 -m venv "$VENV_DIR"
fi

# 3. 检查并安装依赖 (补库)
echo "🔍 检查并补全库依赖..."
# 使用 pip 检查关键库，如果不完整则安装
if ! "$VENV_DIR/bin/python" -c "import pikepdf, fitz, customtkinter, flask, dashscope, pdf2image" &> /dev/null; then
    echo "📥 正在安装/更新库依赖，请稍候..."
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败，请检查网络连接。"
        read -p "按回车键退出..."
        exit 1
    fi
    echo "✅ 库依赖补全完成！"
else
    echo "✅ 库依赖已就绪。"
fi

# 4. 启动主程序
echo ""
echo "🚀 正在启动主菜单..."
"$VENV_DIR/bin/python" launcher.py

# 如果程序意外退出，保持窗口开启
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 程序运行过程中出现错误。"
    read -p "按回车键关闭窗口..."
fi
