# -*- coding: utf-8 -*-
import os
import json
import sys
from pathlib import Path

# Base directories
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TEMP_DIR = os.path.join(BASE_DIR, "temp_images")

# Global config locations
APP_CONFIG_DIR = Path.home() / ".qushuiyin"
APP_CONFIG_FILE = APP_CONFIG_DIR / "config.json"
API_KEY_FILE = os.path.join(BASE_DIR, ".qwen_key")

DEFAULT_CONFIG = {
    "window": {
        "width": 1200, "height": 800, "x": None, "y": None, "maximized": False
    },
    "theme": {
        "mode": "light", "color_theme": "blue"
    },
    "api_keys": {
        "dashscope": ""
    },
    "preferences": {
        "dpi": 150,
        "scan_limit": 5,
        "default_mode": "actual"
    }
}

def ensure_dirs():
    for d in [INPUT_DIR, OUTPUT_DIR, TEMP_DIR, str(APP_CONFIG_DIR)]:
        os.makedirs(d, exist_ok=True)

def load_config():
    config = DEFAULT_CONFIG.copy()
    
    # Load from system config
    if APP_CONFIG_FILE.exists():
        try:
            with open(APP_CONFIG_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                # Deep merge logic could go here, but simple update for now
                for key in saved:
                    if isinstance(config.get(key), dict) and isinstance(saved[key], dict):
                        config[key].update(saved[key])
                    else:
                        config[key] = saved[key]
        except Exception:
            pass

    # Backwards compatibility for .qwen_key
    if os.path.exists(API_KEY_FILE):
        try:
            with open(API_KEY_FILE, "r", encoding="utf-8") as f:
                key = f.read().strip()
                if key:
                    config["api_keys"]["dashscope"] = key
        except Exception:
            pass
            
    return config

def save_config(config):
    ensure_dirs()
    try:
        with open(APP_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            
        # Also sync to .qwen_key for legacy scripts
        if config["api_keys"].get("dashscope"):
            with open(API_KEY_FILE, "w", encoding="utf-8") as f:
                f.write(config["api_keys"]["dashscope"])
    except Exception as e:
        print(f"Error saving config: {e}")

def get_api_key(provider="dashscope"):
    config = load_config()
    return config["api_keys"].get(provider, "")
