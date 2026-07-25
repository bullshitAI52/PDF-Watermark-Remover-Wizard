#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图形化系统设置：管理 DashScope API Key 并测试云端连接。"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
import sys
from pathlib import Path

try:
    import customtkinter as ctk
    from tkinter import messagebox
except ImportError:
    print("缺少 customtkinter，请先安装项目依赖。")
    raise SystemExit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from utils.config_manager import get_api_key, load_config, save_config


class SettingsApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PDF 水印清理助手 - 系统设置")
        self.geometry("560x500")
        self.resizable(False, False)
        ctk.set_appearance_mode(load_config().get("theme", {}).get("mode", "light"))
        self._build_ui()

    def _build_ui(self):
        root = ctk.CTkFrame(self, fg_color="transparent")
        root.pack(fill="both", expand=True, padx=28, pady=24)
        ctk.CTkLabel(root, text="系统设置", font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(root, text="仅云端 AI 图像修补模式需要配置 API Key。", text_color="#888888", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(2, 20))

        ctk.CTkLabel(root, text="DashScope API Key", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        self._key_entry = ctk.CTkEntry(root, show="•", placeholder_text="粘贴新的 API Key")
        self._key_entry.pack(fill="x", pady=(6, 5))
        existing = get_api_key()
        self._key_status = ctk.CTkLabel(root, text=self._key_status_text(existing), text_color="#888888")
        self._key_status.pack(anchor="w")

        actions = ctk.CTkFrame(root, fg_color="transparent")
        actions.pack(fill="x", pady=(14, 18))
        actions.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(actions, text="保存密钥", command=self._save_key).grid(row=0, column=0, padx=(0, 4), sticky="ew")
        self._test_button = ctk.CTkButton(actions, text="测试云端连接", command=self._test_connection)
        self._test_button.grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(actions, text="清除密钥", fg_color="#95A5A6", hover_color="#7F8C8D", command=self._clear_key).grid(row=0, column=2, padx=(4, 0), sticky="ew")

        notice = ctk.CTkFrame(root, fg_color=("#FFF7E6", "#463B27"), corner_radius=8)
        notice.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(
            notice,
            text=("云端模式提示\n"
                  "• 使用时会将待修复页面上传至 DashScope；请确认文件不含不应上传的内容。\n"
                  "• 云端调用可能产生费用，具体以您的服务商账户和价格为准。\n"
                  "• “测试云端连接”会发送一条极短测试请求，不会上传 PDF。"),
            justify="left", anchor="w", font=ctk.CTkFont(size=11),
        ).pack(fill="x", padx=14, pady=12)
        self._result = ctk.CTkLabel(root, text="", justify="left", anchor="w", wraplength=500)
        self._result.pack(fill="x")

    @staticmethod
    def _key_status_text(key: str) -> str:
        return f"当前状态：已配置（{key[:4]}…{key[-4:]}）" if len(key) >= 8 else "当前状态：未配置"

    def _save_key(self):
        key = self._key_entry.get().strip()
        if not key:
            self._result.configure(text="请输入 API Key 后再保存。", text_color="#C0392B")
            return
        config = load_config()
        config["api_keys"]["dashscope"] = key
        save_config(config)
        self._key_entry.delete(0, "end")
        self._key_status.configure(text=self._key_status_text(key))
        self._result.configure(text="✓ API Key 已保存。", text_color="#27AE60")

    def _clear_key(self):
        if not get_api_key():
            self._result.configure(text="当前没有已保存的 API Key。", text_color="#888888")
            return
        if not messagebox.askyesno("清除 API Key", "确定清除已保存的 DashScope API Key 吗？", parent=self):
            return
        config = load_config()
        config["api_keys"]["dashscope"] = ""
        save_config(config)
        self._key_entry.delete(0, "end")
        self._key_status.configure(text=self._key_status_text(""))
        self._result.configure(text="✓ API Key 已清除。", text_color="#27AE60")

    def _test_connection(self):
        key = self._key_entry.get().strip() or get_api_key()
        if not key:
            self._result.configure(text="请先保存或输入 API Key。", text_color="#C0392B")
            return
        self._test_button.configure(state="disabled")
        self._result.configure(text="正在测试云端连接…", text_color="#888888")
        threading.Thread(target=self._run_connection_test, args=(key,), daemon=True).start()

    def _run_connection_test(self, key: str):
        payload = json.dumps({"model": "qwen-turbo", "input": {"messages": [{"role": "user", "content": "连接测试"}]}, "parameters": {"result_format": "message"}}).encode("utf-8")
        request = urllib.request.Request(
            "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
            data=payload,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                code = response.status
            message, color = ("✓ 云端连接正常。", "#27AE60") if 200 <= code < 300 else (f"连接返回 HTTP {code}。", "#E67E22")
        except urllib.error.HTTPError as exc:
            message, color = (f"连接失败：HTTP {exc.code}。请检查 API Key、服务权限或账户额度。", "#C0392B")
        except Exception as exc:
            message, color = (f"连接失败：{exc}。请检查网络后重试。", "#C0392B")
        self.after(0, lambda: self._finish_connection_test(message, color))

    def _finish_connection_test(self, message: str, color: str):
        self._test_button.configure(state="normal")
        self._result.configure(text=message, text_color=color)


def main():
    SettingsApp().mainloop()


if __name__ == "__main__":
    main()
