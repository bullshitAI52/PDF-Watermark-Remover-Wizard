#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import subprocess
import sys
import traceback
from utils.config_manager import load_config, save_config, ensure_dirs, INPUT_DIR
from utils.file_utils import get_supported_files

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MENU_ITEMS = [
    ("1", "🖥️  可视化智能清理 V3 (优化版 - 推荐)", "后台全书同步、自由区域框选、按页导出、可取消。"),
    ("2", "🖥️  可视化智能清理 V2 (经典版)", "原版界面：双击点选、框选Logo、全书同步。"),
    ("4", "🪄  AI 图像修补 (Cloud Mode)", "针对图片型 PDF 的完美背景修复 (需 API Key)。"),
    ("5", "☢️  核弹模式 (Vector Killer)", "强力清除 PDF 中的矢量路径与图形水印。"),
    ("6", "🖼️  本地图片模式 (Offline)", "离线快速清理扫描件背景、图片文件夹。"),
    ("7", "⚙️  系统设置", "配置大模型 API Key 及全局选项。"),
]

# Map choices to script paths
SCRIPT_MAP = {
    "1": ("gui_app/main_v3.py", []),
    "2": ("gui_app/main_v2.py", []),
    "4": ("image_mode_pic_watermark/raster_cleaner.py", ["--mode", "2"]),
    "5": ("core/vector_killer.py", []),
    "6": ("image_mode_pic_watermark/raster_cleaner.py", ["--mode", "1"]),
}

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def set_api_key():
    print("\n--- ⚙️ Set DashScope API Key ---")
    print("Get your key from: https://bailian.console.aliyun.com/")
    config = load_config()
    current_key = config["api_keys"].get("dashscope", "")
    if current_key:
        print(f"Current Key: {current_key[:4]}...{current_key[-4:]}")
    
    key = input("Enter New API Key (or press Enter to keep current): ").strip()
    if key:
        config["api_keys"]["dashscope"] = key
        save_config(config)
        print("✅ Key saved successfully.")
    else:
        print("Operation cancelled.")

def run_script(script_rel_path, args):
    script_path = os.path.join(BASE_DIR, script_rel_path)
    if not os.path.exists(script_path):
        print(f"❌ Error: Script not found at {script_path}")
        return
    
    cmd = [sys.executable, script_path] + args
    subprocess.run(cmd)

def print_menu():
    print("========================================")
    print("    PDF Watermark Remover (Pro V0.3)")
    print("========================================")
    print(f" Detected {len(get_supported_files(INPUT_DIR))} supported files in 'input' folder.")
    print("========================================")
    for key, title, description in MENU_ITEMS:
        print(f"{key}. {title}")
        print(f"       - {description}")
        print("----------------------------------------")
    print("0. ❌  Exit")
    print("========================================")

def launcher_menu():
    ensure_dirs()

    while True:
        clear_screen()
        print_menu()
        choice = input("Choice (0-7): ").strip().lower()

        if choice == "0":
            sys.exit(0)
        elif choice == "7":
            set_api_key()
        elif choice in SCRIPT_MAP:
            script_path, args = SCRIPT_MAP[choice]
            try:
                run_script(script_path, args)
            except Exception as exc:
                print(f"\n❌ Error: {exc}")
                traceback.print_exc()
        else:
            print(f"Invalid choice: {choice}")

        input("\nPress Enter to continue...")

if __name__ == "__main__":
    launcher_menu()
