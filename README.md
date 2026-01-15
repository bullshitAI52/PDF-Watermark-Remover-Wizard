# PDF Watermark Removal Assistant (PDF 水印批量删除助手)

> 🚨 **Disclaimer (免责声明)**:
> 本工具仅供**个人学习、安全研究和档案管理**使用。严禁用于任何商业用途或去除版权保护。
> This tool is for **educational and personal archive purposes only**. Strictly PROHIBITED for commercial use.

[English Guide](#english) | [中文说明](#chinese)

---

<a name="english"></a>
## 🇬🇧 English Guide

A powerful AI-driven tool to remove watermarks from PDFs. Supports Text, Vectors, and Scanned Images.

### 🚀 Quick Start
1.  **Put PDFs** into the **`input`** folder (Root directory).
2.  **Double-click** `start_mac.command` (Mac).
3.  **Get cleaned files** from the **`output`** folder.

### 🛠️ The 6 Modes

*   **1. 🚀 One-Click AI (Text Only)**:
    *   **Best for**: Standard PDFs with selectable text watermarks.
    *   **Input**: PDF Only.
*   **2. 🪄 Wizard Mode (Interactive)**:
    *   **Best for**: Safety first. It asks you "Delete this?" for every suspect found.
    *   **Input**: PDF Only.
*   **3. 👁️ Vision AI (Detection)**:
    *   **Best for**: Diagnosing what the watermark text is using AI Vision.
    *   **Input**: PDF Only.
*   **4. ☁️ AI Inpainting (Universal)**:
    *   **Best for**: **Images** or **Complex PDFs** where watermark is part of the background.
    *   **Input**: PDF + **Images (.jpg/.png)**.
    *   **Note**: Uses Aliyun Cloud AI (Requires API Key).
*   **5. ☢️ Nuclear Mode (Vector Killer)**:
    *   **Best for**: Stubborn graphics, lines, shapes, and vector drawings not selectable as text.
    *   **Input**: PDF Only.
*   **6. 🖼️ Local Image Mode (Speed)**:
    *   **Best for**: **Scanned PDFs** or **Images**. Converts everything to pixels and cleans white noise.
    *   **Input**: PDF + **Images (.jpg/.png)**.
    *   **Note**: Free, fast, offline.

---

<a name="chinese"></a>
## 🇨🇳 中文说明 (Chinese Guide)

最全能的 PDF/图片 去水印工具，整合了 6 种不同的清洗引擎。

### 🚀 快速开始 (3步搞定)
1.  把你的文件 (PDF 或 图片) 放入 **`input`** 文件夹。
2.  双击运行 **`start_mac.command`**。
3.  输入 **1-6** 选择模式，回车。
4.  去 **`output`** 文件夹领取处理好的文件。

### 🛠️ 六大模式详解

#### 🟢 文本/结构组 (仅支持 PDF)
*   **1. 🚀 One-Click AI (一键文本)**
    *   **适用**: 90% 的普通文档，水印是能选中的文字。
    *   **特点**: 速度快，保留原文档结构。
*   **2. 🪄 Wizard Mode (安全向导)**
    *   **适用**: 怕模式1误删正文时用。
    *   **特点**: 交互式删除，AI 找到水印后会问你确认。
*   **3. 👁️ Vision AI (视觉侦查)**
    *   **适用**: 不知道水印是啥，或者乱码。
    *   **特点**: AI "看" 一眼第一页，告诉你水印的内容。
*   **5. ☢️ Nuclear Mode (核弹向量)**
    *   **适用**: **矢量水印**、删不掉的图形、线条、阴影。
    *   **特点**: 暴力扫描底层指令，移除特定颜色的绘图对象。

#### 🔴 图像/全能组 (支持 PDF + 图片)
*   **4. ☁️ AI Inpainting (AI 消除笔)**
    *   **适用**: **图片文件** (`.jpg/.png`) 或 **背景复杂** 的 PDF。
    *   **特点**: **调用阿里云万象大模型**，像 PS 里的“内容识别填充”一样把水印 P 掉。
    *   **注意**: 效果最好，但需要 API Key。
*   **6. 🖼️ Local Image Mode (本地图片)**
    *   **适用**: **扫描件 PDF** 或 **图片文件**。
    *   **特点**: 强制把文件转为图片 -> 本地算法(CV2)漂白背景 -> 重新合成。
    *   **注意**: **速度飞快，免费**，但会损失 PDF 的文本层（变成纯图片 PDF）。

### 📦 常见问题
*   **Q: 怎么获取 API Key?**
    *   A: 如果要用模式 4 (AI Inpainting) 或 3 (Vision)，你需要阿里云 DashScope 的 Key。把 Key 放在 `.qwen_key` 文件里即可。
*   **Q: 模式 5 误删了表格线条怎么办？**
    *   A: 核弹模式比较暴力。如果是普通水印，建议先用模式 1。

---
**Enjoy your clean PDFs!**
