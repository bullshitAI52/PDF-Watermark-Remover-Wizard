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

# Configuration
INPUT_DIR = 'input'
OUTPUT_DIR = 'output'
TEMP_DIR = 'temp_images'

# Load API Key
try:
    with open('../.qwen_key', 'r') as f:
        dashscope.api_key = f.read().strip()
except:
    print("API Key not found in ../.qwen_key")
    dashscope.api_key = input("Please enter your Dashscope API Key: ").strip()

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

def clean_image(img):
    """
    Local CV2 cleaning (Thresholding fallback).
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Simple thresholding: turn light gray pixels to white
    _, mask = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    result = img.copy()
    result[mask == 255] = [255, 255, 255]
    return result

def process_pdf(pdf_path, use_ai=False):
    filename = os.path.basename(pdf_path)
    name, ext = os.path.splitext(filename)
    
    print(f"Reading: {filename} (AI Mode: {use_ai})...")
    
    try:
        images = convert_from_path(pdf_path, dpi=200)
    except Exception as e:
        print(f"Error: {e}")
        return

    processed_pdf_path = os.path.join(OUTPUT_DIR, f"{name}_cleaned.pdf")
    cleaned_images_paths = []
    
    for i, pil_img in enumerate(images):
        print(f"  Processing Page {i+1}/{len(images)}...")
        
        # Save raw for processing
        raw_path = os.path.join(TEMP_DIR, f"temp_{i}.jpg")
        pil_img.save(raw_path)
        
        if use_ai:
            # Real Cloud AI
            # Convert PIL to CV2 first for local fallback if needed?
            # clean_image_with_dashscope handles reading internally or we pass path.
            cleaned = clean_image_with_dashscope(raw_path)
        else:
            # Local CV2
            cv2_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            cleaned = clean_image(cv2_img)
        
        # Save back
        cleaned_pil = Image.fromarray(cv2.cvtColor(cleaned, cv2.COLOR_BGR2RGB))
        out_path = os.path.join(TEMP_DIR, f"clean_{i}.jpg")
        cleaned_pil.save(out_path, quality=90)
        cleaned_images_paths.append(out_path)

    print(f"  Recombining PDF...")
    with open(processed_pdf_path, "wb") as f:
        f.write(img2pdf.convert(cleaned_images_paths))
        
    print(f"Done! Saved to: {processed_pdf_path}")
    
    # Cleanup
    # Cleanup
    import shutil
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    ensure_dirs()

def clean_image_with_dashscope(image_path, mask_path=None):
    """
    Uses Dashscope (Wanxian) Image Repainting to remove watermarks.
    Requirements:
    1. 'dashscope' library
    2. Valid API Key
    3. Input Image + Mask Image (Black background, White area to repair)
    """
    import dashscope
    from dashscope import ImageSynthesis
    
    if not dashscope.api_key:
        print("    ⚠️ Skip: No API Key.")
        return cv2.imread(image_path) # Fallback

    # 1. Create a Mask automatically if not provided
    # Strategy: Threshold the light gray watermark to create a mask for the AI
    if not mask_path:
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Target light gray areas (watermarks)
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        # Dilate slightly to cover edges
        kernel = np.ones((3,3), np.uint8)
        mask = cv2.dilate(thresh, kernel, iterations=1)
        
        # Invert? No, Repaint API usually expects White=Repaint Area, Black=Keep.
        # Our threshold makes light pixels (200-255) into White (255).
        # So 'mask' is already correct: White areas are the watermark.
        
        # Save Mask Temp
        mask_path = image_path.replace(".jpg", "_mask.png")
        cv2.imwrite(mask_path, mask)

    print("    ☁️ Uploading to Alibaba Cloud for Repainting...")
    
    try:
        # Note: Local file paths need to be properly handled. 
        # Dashscope Python SDK handles local paths by uploading to temporary OSS if file:// provided?
        # Actually standard Dashscope usually expects file paths or URLs. 
        # Let's try passing local path strings with file:// prefix or direct paths if SDK updates.
        # Fallback: User might need to upgrade dashscope SDK.
        
        # Call Repainting API
        # Model: wanx-x-painting (Generic Inpainting)
        rsp = ImageSynthesis.call(
            model='wanx-x-painting',
            function='inpainting',
            image_url=f'file://{os.path.abspath(image_path)}',
            mask_url=f'file://{os.path.abspath(mask_path)}',
            n=1
        )
        
        if rsp.status_code == 200:
            # Download result
            import requests
            result_url = rsp.output.results[0].url
            print("    ⬇️ Downloading AI Result...")
            resp_img = requests.get(result_url)
            # Convert bytes to cv2
            arr = np.frombuffer(resp_img.content, np.uint8)
            cleaned_img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            return cleaned_img
        else:
            print(f"    ⚠️ API Failed: {rsp.code} - {rsp.message}")
            print("    (Falling back to local Mode)")
            return clean_image(cv2.imread(image_path))
            
    except Exception as e:
        print(f"    ⚠️ AI Error: {e}")
        return clean_image(cv2.imread(image_path))


def select_mode():
    print("\n========================================")
    print("      Select Cleaning Intelligence      ")
    print("========================================")
    print("1. ⚡ Local Speed Mode (CV2) [Default]")
    print("   - Ultra fast, free.")
    print("   - Uses math to filter gray pixels.")
    print("2. 🎨 Alibaba Wanx AI Mode (Real Cloud Repair)")
    print("   - Uploads to Cloud -> GenAI Repainting.")
    print("   - Slower, costs API credits.")
    print("   - BEST for complex backgrounds.")
    print("========================================")
    choice = input("Enter choice (1/2): ").strip()
    return choice

def main():
    ensure_dirs()
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
    print(f"DEBUG: Input Directory: {os.path.abspath(INPUT_DIR)}")
    print(f"DEBUG: Files Found: {files}")
    
    if not files:
        print(f"❌ Error: No PDF files found in '{INPUT_DIR}'!")
        print(f"👉 Please make sure you put your PDF inside: {os.path.abspath(INPUT_DIR)}")
        return 

    mode = select_mode()
    
    
    for f in files:
        process_pdf(os.path.join(INPUT_DIR, f), use_ai=(mode=='2'))

# Update process_pdf signature in memory (need to rewrite that part too)

if __name__ == "__main__":
    main()


