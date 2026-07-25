#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import subprocess
import sys
import traceback
from utils.config_manager import ensure_dirs, INPUT_DIR
from utils.file_utils import get_supported_files

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MENU_ITEMS = [
    ("1", "🖥️  可视化智能清理（推荐）", "直接选择 PDF、点选/框选水印、可同步到全书。"),
    ("2", "🪄  AI 图像修补（云端）", "适用于复杂扫描件；需配置 API Key，可能产生费用。"),
    ("3", "☢️  矢量强力清理", "批量删除矢量图形；请先备份原文件并检查输出。"),
    ("4", "🖼️  本地图片清理", "离线处理扫描件或图片，速度快但会转为图像。"),
    ("5", "⚙️  系统设置", "图形化配置 API Key、测试云端连接与查看隐私提示。"),
]

# Map choices to script paths
SCRIPT_MAP = {
    "1": ("gui_app/main_v3.py", []),
    "2": ("image_mode_pic_watermark/raster_cleaner.py", ["--mode", "2"]),
    "3": ("core/vector_killer.py", []),
    "4": ("image_mode_pic_watermark/raster_cleaner.py", ["--mode", "1"]),
    "5": ("gui_app/settings_window.py", []),
}

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def run_script(script_rel_path, args):
    script_path = os.path.join(BASE_DIR, script_rel_path)
    if not os.path.exists(script_path):
        print(f"❌ Error: Script not found at {script_path}")
        return
    
    cmd = [sys.executable, script_path] + args
    subprocess.run(cmd)

def print_menu():
    print("========================================")
    print("       PDF 水印清理助手")
    print("========================================")
    print(f" input/ 中有 {len(get_supported_files(INPUT_DIR))} 个待处理文件")
    print(" 直接回车即可打开推荐的可视化清理模式。")
    print("========================================")
    for key, title, description in MENU_ITEMS:
        print(f"{key}. {title}")
        print(f"       - {description}")
        print("----------------------------------------")
    print("0. 退出")
    print("========================================")

def launcher_menu():
    ensure_dirs()

    while True:
        clear_screen()
        print_menu()
        choice = input("请选择模式 [默认 1]：").strip().lower() or "1"

        if choice == "0":
            sys.exit(0)
        elif choice in SCRIPT_MAP:
            script_path, args = SCRIPT_MAP[choice]
            try:
                run_script(script_path, args)
            except Exception as exc:
                print(f"\n❌ Error: {exc}")
                traceback.print_exc()
        else:
            print(f"无效选择：{choice}")

        input("\n按回车键返回主菜单…")

if __name__ == "__main__":
    launcher_menu()
