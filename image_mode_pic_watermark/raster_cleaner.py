# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# PDF Watermark Removal Assistant
# DISCLAIMER: This tool is for PERSONAL STUDY & RESEARCH ONLY.
# STRICTLY PROHIBITED FOR COMMERCIAL USE or ILLEGAL ACTIVITIES.
# The author assumes NO LIABILITY for any misuse of this software.
# 免责声明：本工具仅供个人学习研究，严禁用于商业或非法用途。作者不对任何滥用后果负责。
# -----------------------------------------------------------------------------
import os
import sys
import numpy as np
import cv2
from pdf2image import convert_from_path
import img2pdf
from PIL import Image
import dashscope
from dashscope import MultiModalConversation
import time

# Configuration
INPUT_DIR = 'input'
OUTPUT_DIR = 'output'
TEMP_DIR = 'temp_images'

# Global State
AI_QUOTA_EXCEEDED = False

# Load API Key
try:
    # Try looking in parent directory if running from subdirectory
    possible_keys = ['.qwen_key', '../.qwen_key', '../../.qwen_key']
    found_key = False
    for k in possible_keys:
        if os.path.exists(k):
             with open(k, 'r') as f:
                dashscope.api_key = f.read().strip()
                found_key = True
                break
except:
    pass

if not found_key and not dashscope.api_key:
    # prompt only if interactive? Or just skip
    pass

def ensure_dirs():
    if not os.path.exists(INPUT_DIR): os.makedirs(INPUT_DIR)
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    if not os.path.exists(TEMP_DIR): os.makedirs(TEMP_DIR)

def clean_image_with_ai(image_path):
    """
    Uses Qwen-VL-Max to decide how to clean the image, or (simpler) uses CV2.
    NOTE: Sending every page to Qwen-VL is slow and expensive.
    For this prototype, we will stick to Local CV2 but add the 'Structure' for AI call.
    """
    # Placeholder for actual VL call if user insists on API doing the pixel work
    # (Realistically, VL models return description, not edited image bytes directly roughly)
    # So we use CV2 for now, but label it "AI-ready".
    
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    result = img.copy()
    result[mask == 255] = [255, 255, 255]
    return result

def clean_image(img, margin_pct=0):
    """
    Local CV2 cleaning with Green/Cyan Filter + Margin Eraser.
    margin_pct: Percentage of top/bottom to erase (e.g. 10 for 10%).
    """
    rows, cols, _ = img.shape
    
    # 0. Apply Margin Eraser (Blind Cut)
    
    # 0. Apply Margin Eraser (Blind Cut)
    # Support dictionary or simple usage
    top_pct = 0
    bottom_pct = 0
    
    if isinstance(margin_pct, dict):
        top_pct = margin_pct.get('top', 0)
        bottom_pct = margin_pct.get('bottom', 0)
    else:
        top_pct = margin_pct
        bottom_pct = margin_pct

    if top_pct > 0:
        cut_h_top = int(rows * (top_pct / 100))
        img[0:cut_h_top, :] = [255, 255, 255] # White out Top
        
    if bottom_pct > 0:
        cut_h_bot = int(rows * (bottom_pct / 100))
        img[rows-cut_h_bot:rows, :] = [255, 255, 255] # White out Bottom
    
    # 1. Convert to HSV
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # 2. Define Green/Cyan Range
    # Cyan/Green is roughly 35-90 in OpenCV Hue (0-179)
    # Saturation usually > 20 (not gray), Value > 100 (not black)
    lower_green = np.array([30, 20, 100])
    upper_green = np.array([100, 255, 255])
    green_mask = cv2.inRange(hsv, lower_green, upper_green)

    # 2b. Magic Lion Orange (Hue ~10-30)
    lower_orange = np.array([5, 50, 50])
    upper_orange = np.array([35, 255, 255])
    orange_mask = cv2.inRange(hsv, lower_orange, upper_orange)
    
    # 2c. Magic Lion Dark Cyan (Hue ~90-110, but Darker)
    lower_dark_cyan = np.array([80, 20, 50]) # Broad range for the dark text
    upper_dark_cyan = np.array([130, 255, 200])
    cyan_mask = cv2.inRange(hsv, lower_dark_cyan, upper_dark_cyan)

    # 2d. Faint Orange/Beige (For "Aimufasa" Watermark)
    # Hue: 0-40 (Red-Yellow), Saturation: 5-60 (Faint), Value: 180-255 (Bright)
    lower_faint = np.array([0, 5, 180])
    upper_faint = np.array([40, 60, 255])
    faint_mask = cv2.inRange(hsv, lower_faint, upper_faint)
    
    # Combined Color Mask
    color_mask = cv2.bitwise_or(green_mask, orange_mask)
    color_mask = cv2.bitwise_or(color_mask, cyan_mask)
    color_mask = cv2.bitwise_or(color_mask, faint_mask)

    # 4. Dilate mask slightly to catch edges
    kernel = np.ones((2,2), np.uint8)
    color_mask = cv2.dilate(color_mask, kernel, iterations=1)
    
    # 5. Also remove light gray background noise (Original Logic)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, gray_mask = cv2.threshold(gray, 210, 255, cv2.THRESH_BINARY)
    
    # Apply: Turn masked pixels WHITE
    result = img.copy()
    result[color_mask > 0] = [255, 255, 255] # Erase Colors
    # result[gray_mask == 255] = [255, 255, 255] # Optional: Clean background
    
    return result

def process_file(file_path, use_ai=False, margin_pct=0):
    filename = os.path.basename(file_path)
    name, ext = os.path.splitext(filename)
    ext = ext.lower()
    
    print(f"Processing: {filename} (AI Mode: {use_ai}, Margin Cut: {margin_pct}%)...")

    # Case A: PDF
    if ext == '.pdf':
        try:
            images = convert_from_path(file_path, dpi=200)
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return

        processed_pdf_path = os.path.join(OUTPUT_DIR, f"{name}_cleaned.pdf")
        cleaned_images_paths = []
        
        for i, pil_img in enumerate(images):
            print(f"  Page {i+1}/{len(images)}...")
            
            # Save raw for processing
            raw_path = os.path.join(TEMP_DIR, f"temp_{i}.jpg")
            pil_img.save(raw_path)
            
            cleaned_img_arr = process_single_image(raw_path, use_ai, margin_pct)
            
            # Save back
            cleaned_pil = Image.fromarray(cv2.cvtColor(cleaned_img_arr, cv2.COLOR_BGR2RGB))
            out_path = os.path.join(TEMP_DIR, f"clean_{i}.jpg")
            cleaned_pil.save(out_path, quality=90)
            cleaned_images_paths.append(out_path)

        print(f"  Recombining PDF...")
        with open(processed_pdf_path, "wb") as f:
            f.write(img2pdf.convert(cleaned_images_paths))
            
        print(f"Done! Saved to: {os.path.abspath(processed_pdf_path)}")
        
    # Case B: Image (JPG, PNG, JPEG)
    elif ext in ['.jpg', '.jpeg', '.png']:
        cleaned_img_arr = process_single_image(file_path, use_ai, margin_pct)
        
        out_name = f"{name}_cleaned{ext}"
        out_path = os.path.join(OUTPUT_DIR, out_name)
        
        cv2.imwrite(out_path, cleaned_img_arr)
        print(f"Done! Saved to: {out_path}")

def process_single_image(image_path, use_ai, margin_pct):
    """
    Helper to process one image file (path) and return CV2 array.
    """
    if use_ai:
        if AI_QUOTA_EXCEEDED:
             print("    ℹ️ (Skipping AI due to Quota Limit -> Local Mode)")
             return clean_image(cv2.imread(image_path), margin_pct)
        else:
            time.sleep(1) # Rate limit
            return clean_image_with_dashscope(image_path)
    else:
        # Local CV2
        img = cv2.imread(image_path)
        if img is None:
             print(f"Error reading image: {image_path}")
             return np.zeros((100,100,3), np.uint8)
        return clean_image(img, margin_pct)

def clean_image_with_dashscope(image_path, mask_path=None):
    """
    Uses Dashscope (Wanxian) Image Repainting to remove watermarks.
    """
    import dashscope
    from dashscope import ImageSynthesis
    
    if not dashscope.api_key:
        print("    ⚠️ Skip: No API Key.")
        return cv2.imread(image_path) # Fallback

    # 1. Create a Mask automatically if not provided
    if not mask_path:
        img = cv2.imread(image_path)
        if img is None: return None
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        kernel = np.ones((3,3), np.uint8)
        mask = cv2.dilate(thresh, kernel, iterations=1)
        mask_path = image_path.replace(".jpg", "_mask.png")
        cv2.imwrite(mask_path, mask)

    print("    ☁️ Uploading to Alibaba Cloud for Repainting...")
    
    try:
        rsp = ImageSynthesis.call(
            model='wanx-x-painting',
            function='inpainting',
            prompt="background", 
            image_url=f'file://{os.path.abspath(image_path)}',
            mask_url=f'file://{os.path.abspath(mask_path)}',
            n=1
        )
        
        if rsp.status_code == 200:
            import requests
            result_url = rsp.output.results[0].url
            print("    ⬇️ Downloading AI Result...")
            resp_img = requests.get(result_url)
            arr = np.frombuffer(resp_img.content, np.uint8)
            cleaned_img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            return cleaned_img
        else:
            print(f"    ⚠️ API Failed: {rsp.code} - {rsp.message}")
            return clean_image(cv2.imread(image_path))
            
    except Exception as e:
        print(f"    ⚠️ AI Error: {e}")
        e_str = str(e)
        if "Throttling.AllocationQuota" in e_str or "403" in e_str:
             global AI_QUOTA_EXCEEDED
             AI_QUOTA_EXCEEDED = True
             print("    🛑 Critical: Free allocated quota exceeded. Switching to LOCAL MODE.")
        return clean_image(cv2.imread(image_path))

def select_mode():
    print("\n========================================")
    print("      Select Cleaning Intelligence      ")
    print("========================================")
    print("1. ⚡ Local Speed Mode (CV2) [Default]")
    print("   - Ultra fast, free.")
    print("   - Uses math to filter gray/color pixels.")
    print("   - RECOMMENDED (Since AI Quota might be empty).")
    print("2. 🎨 Alibaba Wanx AI Mode (Real Cloud Repair)")
    print("   - Uploads to Cloud -> GenAI Repainting.")
    print("   - Slower, costs API credits.")
    print("   - ONLY choose this if you have paid quota.")
    print("========================================")
    choice = input("Enter choice (1/2) [Default: 1]: ").strip()
    if not choice: return '1'
    return choice

def main():
    ensure_dirs()
    # Support PDF and Images
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png'))]
    
    print(f"DEBUG: Input Directory: {os.path.abspath(INPUT_DIR)}")
    print(f"DEBUG: Files Found: {files}")
    
    if not files:
        print(f"❌ Error: No supported files (PDF/JPG/PNG) found in '{INPUT_DIR}'!")
        print(f"👉 Please put your files inside: {os.path.abspath(INPUT_DIR)}")
        return 

    # Check for CLI args to bypass interaction
    # usage: python raster_cleaner.py --mode 1 --margin 10
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['1', '2'], help='Mode 1: Local, Mode 2: AI')
    parser.add_argument('--margin', type=str, default="0", help='Margin percentage cut. Single number (e.g. 10) for both, or "10,5" for Top,Bottom')
    args, unknown = parser.parse_known_args()
    
    if args.mode:
        mode = args.mode
        # Parse margin "10" or "10,5" (top, bottom)
        if ',' in str(args.margin):
            parts = str(args.margin).split(',')
            margin_pct = {'top': int(parts[0]), 'bottom': int(parts[1])}
        else:
            margin_pct = int(args.margin)
    else:
        mode = select_mode()
        # Ask about margins if Mode 1
        margin_pct = 0
        if mode == '1':
            print("\n--- Header/Footer Cleaning ---")
            cut = input("Erase Top/Bottom X%? (Enter '10' for 10%, or Enter to skip): ").strip()
            if cut.isdigit():
                margin_pct = int(cut)
    
    for f in files:
        process_file(os.path.join(INPUT_DIR, f), use_ai=(mode=='2'), margin_pct=margin_pct)
    
    # Cleanup
    import shutil
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    ensure_dirs()


if __name__ == "__main__":
    main()


