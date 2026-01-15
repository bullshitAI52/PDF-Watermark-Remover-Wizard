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
import concurrent.futures

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR, 'input')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
TEMP_DIR = os.path.join(BASE_DIR, 'temp_images')

# Global State
AI_QUOTA_EXCEEDED = False

# Load API Key
try:
    # Try looking in parent directory if running from subdirectory
    possible_keys = ['.qwen_key', '../.qwen_key', '../../.qwen_key', '../src/.qwen_key']
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

def process_page_task(args):
    """
    Worker function for parallel processing.
    args: (index, image_array (numpy), use_ai, margin_pct)
    """
    i, img_arr, use_ai, margin_pct = args
    
    # 1. AI check
    # Note: AI parallel might hit rate limits faster, but let's allow it logic-wise or prevent it.
    # Since 'AI' here uses 'AI_QUOTA_EXCEEDED' global, which doesn't work well across processes without Manager,
    # we will assume Local Mode is the primary target for parallel speedup. 
    # AI Mode usually requires file upload anyway, so we might skip parallel for AI mode inside this function if needed,
    # OR just be careful. For now, we support local.
    
    if use_ai:
        # Saving to temp is needed for AI API usually, but here we just return control
        # Because global variable AI_QUOTA_EXCEEDED won't sync easily.
        # Fallback to single threaded logic if needed, OR just run local logic.
        # For this optimization, we prioritize Local Speed.
        pass

    # Processing
    # Convert RGB (PIL/pdf2image default) to BGR (OpenCV)
    img_bgr = cv2.cvtColor(img_arr, cv2.COLOR_RGB2BGR)
    cleaned = clean_image(img_bgr, margin_pct)
    
    # Convert back to RGB for saving
    cleaned_rgb = cv2.cvtColor(cleaned, cv2.COLOR_BGR2RGB)
    
    return (i, cleaned_rgb)

def process_file(file_path, use_ai=False, margin_pct=0):
    filename = os.path.basename(file_path)
    name, ext = os.path.splitext(filename)
    ext = ext.lower()
    
    print(f"Processing: {filename} (AI Mode: {use_ai}, Margin Cut: {margin_pct}%)...")

    # Case A: PDF
    if ext == '.pdf':
        try:
            print("  Loading PDF pages...")
            # Convert all at once (Memory intensive for huge files, but fastest for average files)
            images = convert_from_path(file_path, dpi=200)
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return

        processed_pdf_path = os.path.join(OUTPUT_DIR, f"{name}_cleaned.pdf")
        
        # Prepare Tasks
        tasks = []
        for i, pil_img in enumerate(images):
            # Convert PIL to Numpy Array (RGB)
            img_arr = np.array(pil_img)
            tasks.append((i, img_arr, use_ai, margin_pct))
            
        print(f"  Cleaning {len(images)} pages (Parallel)...")
        
        results = []
        if use_ai:
            # AI Mode: Serial processing to respect rate limits and simpler state managment
            print("  (AI Mode active: Running sequentially to avoid rate limits)")
            for task in tasks:
                 # Revert to old temp file logic? No, just adapt task.
                 # But wait, the task function expects numpy.
                 # Let's just run logic here for AI.
                 idx = task[0]
                 print(f"    Page {idx+1}/{len(images)}...", end='\r')
                 # Save temp for AI upload
                 raw_path = os.path.join(TEMP_DIR, f"temp_{idx}.jpg")
                 # Convert task numpy back to BGR for saving, or just use PIL from 'images' list
                 images[idx].save(raw_path)
                 
                 cleaned_bgr = process_single_image(raw_path, True, margin_pct)
                 cleaned_rgb = cv2.cvtColor(cleaned_bgr, cv2.COLOR_BGR2RGB)
                 results.append((idx, cleaned_rgb))
        else:
            # Parallel Local Mode
            with concurrent.futures.ProcessPoolExecutor() as executor:
                for result in executor.map(process_page_task, tasks):
                    results.append(result)
                    print(f"  Finished Page {result[0]+1}/{len(images)}", end='\r')

        # Sort results by index just in case
        results.sort(key=lambda x: x[0])
        
        print(f"\n  Recombining PDF...")
        
        # Cleaned images to bytes
        pdf_bytes_list = []
        for _, img_rgb in results:
            pil_out = Image.fromarray(img_rgb)
            # Save to temporary buffer or file? img2pdf likes files or raw bytes.
            # Using memory buffer:
            # img2pdf.convert(pil_image.tostring()) ? No, img2pdf wants jpeg/png bytes usually for size.
            # Let's save to temp dir sequentially to ensure img2pdf works best (it packs JPEGs efficiently).
            # OR just re-enable temp files but only for writing the final output before merge.
            # Actually, img2pdf can take PIL images directly in newer versions or we save to temp.
            # Saving to temp is safer for img2pdf compatibility.
            
            # Using a temp filename based on index
            temp_out = os.path.join(TEMP_DIR, f"final_{_}.jpg")
            pil_out.save(temp_out, quality=90)
            pdf_bytes_list.append(temp_out)

        with open(processed_pdf_path, "wb") as f:
            f.write(img2pdf.convert(pdf_bytes_list))
            
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
    # Windows/Mac multiprocess safe guard
    import multiprocessing
    multiprocessing.freeze_support()
    main()
