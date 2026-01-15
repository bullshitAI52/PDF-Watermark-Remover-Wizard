# PDF Watermark Removal Assistant (PDF 水印批量删除助手)

> 🚨 **Disclaimer & Legal Warning (免责声明与法律警告)**:
>
> 1.  **Purpose**: This tool is developed strictly for **educational, security research, and personal archive purposes only**.
>     本工具仅供**个人学习、安全研究和档案管理**使用。
> 2.  **No Copyright Infringement**: Do NOT use this tool to remove watermarks from copyrighted materials that you do not own or have permission to modify.
>     请勿使用本工具去除您不拥有版权或未获授权的受版权保护文件的水印。
> 3.  **No Liability**: The author assumes **NO responsibility** for any legal consequences, damages, or third-party misuse arising from the Use/Distribution of this software. Any illegal actions committed by users are solely their own responsibility.
>     **作者不对任何因使用、传播本工具而导致的法律后果、损害或第三方滥用行为承担责任。用户的任何违法行为由其本人自行承担，与作者无关。**
> 4.  **Non-Commercial**: Strictly PROHIBITED for any commercial use, including but not limited to selling the software or providing paid watermark removal services.
>     **严禁将本工具用于任何商业用途**（包括但不限于倒卖软件、提供有偿去水印服务等）。
> 5.  **Agreement**: By downloading, installing, or using this tool, you agree to these terms. If you do not agree, please delete the software immediately.
>     **一旦您下载、安装或使用本工具，即表示您同意上述条款。如不同意，请立即删除本软件。**

[English](#english) | [中文说明](#chinese)

<a name="english"></a>
## 🇬🇧 English Guide

This tool uses AI and forensic analysis to automatically remove complex watermarks from PDF files.

### 🚀 Quick Start
1.  **Put PDFs** into the `input` folder.
2.  **Double-click** `fix_and_run_ai.command`.
3.  **Get cleaned files** from the `output` folder.

### 🛠️ Modes
*   **One-Click AI (`start_mac.command`)**: Best for standard files. Uses AI to detect watermarks.
*   **Forensic "Killer" (`src/vector_killer.py`)**: For stubborn watermarks (Shadows, Vectors). Run via terminal: `python src/vector_killer.py`.

---

<a name="chinese"></a>
## 🇨🇳 中文说明

这是一个基于 AI 和深度取证技术的 PDF 水印去除工具，专门用来处理那些“删不掉”的顽固水印。

### 🚀 快速开始 (小白适用)
1.  把你的 PDF 文件放入 **`input`** 文件夹。
2.  双击运行 **`start_mac.command`** (Mac)。
3.  去 **`output`** 文件夹领取处理好的文件。

### 🛠️ 三种模式介绍

#### 1. 全自动 AI 模式 (Level 1)
*   **怎么用**: 运行 `start_mac.command` -> 选择 "Interactive Wizard" 或 "Vision AI"。
*   **适用**: 90% 的常见水印（文字、Logo）。

#### 2. 核弹清洗模式 (Level 3 - 强力推荐)
*   **什么时候用**: 当你发现水印**变色了**、**变成阴影了**、或者**只删了一半**。
*   **怎么用**:
    在终端输入：
    ```bash
    python3 src/vector_killer.py
    ```

#### 5. 图片/扫描件去水印模式 (Image Mode)
*   **适用**: 扫描件、JPG/PNG 图片、或者文字根本选不中的 PDF。
*   **亮点**: **现已支持 JPG/PNG 图片直接去水印！**
*   **怎么用**:
    1. 进入 `image_mode_pic_watermark` 文件夹。
    2. 把文件（PDF 或 JPG/PNG）放入 `input` 文件夹。
    3. 双击运行 `run_image_mode.command`。
    4. **选择模式**:
       - `1`: 本地急速 (Local CV2) - 免费快。
       - `2`: 阿里 AI 修复 (Wanx Cloud) - **推荐**，智能重绘背景，效果惊人。


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

