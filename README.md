# PDF Watermark Removal Assistant (PDF 水印批量删除助手)

> ⚠️ **Disclaimer / 免责声明**:
> This tool is for **Personal Study and Research ONLY**.
> **Strictly PROHIBITED for Commercial Use.**
> 本工具仅供**个人学习与研究**使用。
> **严禁用于任何商业用途**（包括但不限于倒卖软件、有偿去水印服务等）。
> 
> The author bears no responsibility for any legal consequences arising from the use of this tool.
> 作者不对任何因使用本工具导致的法律后果承担责任。

[English](#english) | [中文说明](#chinese)

<a name="english"></a>
## 🇬🇧 English Guide

This tool uses AI and forensic analysis to automatically remove complex watermarks from PDF files.

### 🚀 Quick Start
1.  **Put PDFs** into the `input` folder.
2.  **Double-click** `fix_and_run_ai.command`.
3.  **Get cleaned files** from the `output` folder.

### 🛠️ Modes
*   **One-Click AI (`fix_and_run_ai`)**: Best for standard files. Uses AI to detect watermarks.
*   **Forensic "Killer" (`universal_killer_v2.py`)**: For stubborn watermarks (Shadows, Vectors). Run via terminal: `python universal_killer_v2.py`.

---

<a name="chinese"></a>
## 🇨🇳 中文说明

这是一个基于 AI 和深度取证技术的 PDF 水印去除工具，专门用来处理那些“删不掉”的顽固水印。

### 🚀 快速开始 (小白适用)
1.  把你的 PDF 文件放入 **`input`** 文件夹。
2.  双击运行 **`fix_and_run_ai.command`** (Mac) 或运行脚本。
    *   程序会自动检测水印并删除。
3.  去 **`output`** 文件夹领取处理好的文件。

### 🛠️ 三种模式介绍

#### 1. 全自动 AI 模式 (Level 1)
*   **怎么用**: 直接双击 `fix_and_run_ai.command`。
*   **适用**: 90% 的常见水印（文字、Logo）。
*   **原理**: 调用 AI 智能分析页面内容，自动判断垃圾信息。

#### 2. 人工辅助模式 (Level 2)
*   **怎么用**: 运行 `start_mac.command` -> 选择 "Interactive Wizard"。
*   **适用**: 当 AI 拿不准时，它会列出是个嫌疑对象，问你 "Yes/No"。

#### 3. 核弹清洗模式 (Level 3 - 强力推荐)
*   **什么时候用**: 当你发现水印**变色了**、**变成阴影了**、或者**只删了一半**。
*   **怎么用**:
    在终端输入：
    ```bash
    python3 universal_killer_v2.py
    ```
*   **威力**: 这是一个经过特殊定制的脚本，能强力清除：
    *   ✅ 看不见的透明文字 (`<˛ÆL`)
    *   ✅ 复杂的矢量绘图水印 (蓝色/黑色线条)
    *   ✅ 伪装成阴影的双层水印 (红色分离层)

#### 4. 图片/扫描件去水印模式 (Image Mode)
*   **适用**: 扫描件、或者由图片合成的 PDF（文字选不中）。
*   **原理**: 自动拆解成图片 -> AI/算法修图 -> 重新合成 PDF。
*   **怎么用**:
    1. 进入 `image_mode_pic_watermark` 文件夹。
    2. 双击运行 `run_image_mode.command`。
    3. **选择模式**:
       - `1`: 本地急速 (Local)
       - `2`: 阿里 AI 修复 (Wanx Cloud) - **推荐**，效果最好。


---

## 📦 如何发给别人使用？(Distribution)

如果你想把这个工具发给**没有安装 Python 环境**的朋友使用，建议打包成独立程序：

### 方法 1: 对方懂一点技术
让他安装 Python，然后把整个文件夹发给他，让他按照上面的步骤运行。

### 方法 2: 打包成 EXE/APP (推荐)
你可以使用 `PyInstaller` 把脚本打包成一个可以直接运行的文件。

**安装打包工具**:
```bash
pip install pyinstaller
```

**打包命令 (Mac/Windows 通用)**:
```bash
# 打包全能清洗脚本
pyinstaller --onefile universal_killer_v2.py
```
打包完成后，在 `dist` 文件夹里会生成一个可执行文件。你只需要把**那个文件**发给朋友，他就能用了（不需要装 Python）。

