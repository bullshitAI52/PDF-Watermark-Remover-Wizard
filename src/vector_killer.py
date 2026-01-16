# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Universal PDF Watermark Killer
# DISCLAIMER: This tool is for PERSONAL STUDY & RESEARCH ONLY.
# STRICTLY PROHIBITED FOR COMMERCIAL USE or ILLEGAL ACTIVITIES.
# The author assumes NO LIABILITY for any misuse of this software.
# 免责声明：本工具仅供个人学习研究，严禁用于商业或非法用途。作者不对任何滥用后果负责。
# -----------------------------------------------------------------------------
import pikepdf
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR, 'input')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

print(f"Universal Killer V2: Scanning '{INPUT_DIR}'...")

def get_color_type(operands):
    # Returns: 'BLUE', 'RED', 'BLACK', 'OTHER'
    try:
        vals = [float(x) for x in operands]
    except:
        return 'OTHER'
        
    # 1. Single Value
    if len(vals) == 1:
        v = vals[0]
        if 0.49 <= v <= 0.51: return 'BLUE' # Pattern Blue
        if v < 0.1: return 'BLACK'
        if 0.1 <= v <= 0.95: return 'GRAY' # Light to Dark Gray
        
    # 3. RGB
    elif len(vals) == 3:
        v1, v2, v3 = vals
        if v3 > 0.8 and v3 > v1: return 'BLUE'
        if v3 > 0.4 and v3 > v1 + 0.1: return 'BLUE'
        
        # Red/Shadow (1,0,0)
        if v1 > 0.9 and v2 < 0.1 and v3 < 0.1: return 'RED'
        
        # Black
        if v1 < 0.1 and v2 < 0.1 and v3 < 0.1: return 'BLACK'
        
        # Gray (RGB values roughly equal and not black/white)
        if abs(v1 - v2) < 0.1 and abs(v2 - v3) < 0.1 and 0.1 < v1 < 0.95:
            return 'GRAY'

    elif len(vals) == 4: # CMYK
        c, m, y, k = vals
        if k > 0.9: return 'BLACK'
        if c > 0.5 and y < 0.1: return 'BLUE'
        if k > 0.1 and k < 0.9 and c < 0.1: return 'GRAY'
        
    return 'OTHER'

def process_page(pdf, page, page_num, target_gray=False):
    try:
        commands = pikepdf.parse_content_stream(page)
    except: return 0

    filtered_commands = []
    removed_count = 0
    
    stack = []
    # State: (fill_type, stroke_type)
    current_fill_type = 'BLACK' # Default
    current_stroke_type = 'BLACK' # Default
    
    for operands, operator in commands:
        op = str(operator)
        
        # Stack
        if op == 'q':
            stack.append((current_fill_type, current_stroke_type))
        elif op == 'Q':
            if stack:
                current_fill_type, current_stroke_type = stack.pop()
            else:
                current_fill_type = 'BLACK'
                current_stroke_type = 'BLACK'
                
        # Colors
        elif op in ['sc', 'scn', 'g', 'rg', 'k']: # Fill
            current_fill_type = get_color_type(operands)
            
        elif op in ['SC', 'SCN', 'G', 'RG', 'K']: # Stroke
            current_stroke_type = get_color_type(operands)
            
        # Draw - Decisive Logic
        should_remove = False
        
        # Fill (f, F, f*) - Remove BLUE, RED, and BLACK
        if op in ['f', 'F', 'f*']:
            if current_fill_type in ['BLUE', 'RED', 'BLACK']:
                should_remove = True
            if target_gray and current_fill_type == 'GRAY':
                should_remove = True
            
        # Stroke (S, s) - Remove BLUE only. Protect RED/BLACK lines.
        elif op in ['S', 's']:
            if current_stroke_type == 'BLUE':
                should_remove = True
            elif current_stroke_type == 'RED': 
                # The shadow might be red strokes?
                # Let's remove them too to be safe. Valid diagrams are usually Black.
                should_remove = True
            if target_gray and current_stroke_type == 'GRAY':
                should_remove = True
            
        # Both (B, b) - Remove ANY Bad
        elif op in ['B', 'B*', 'b', 'b*']:
            if current_fill_type in ['BLUE', 'RED']: should_remove = True
            if current_stroke_type in ['BLUE', 'RED']: should_remove = True
            
            # If Black Fill + Black Stroke?
            if current_fill_type == 'BLACK': 
                # Removing B with black fill is safer than removing S.
                should_remove = True

            if target_gray and (current_fill_type == 'GRAY' or current_stroke_type == 'GRAY'):
                should_remove = True

        if should_remove:
            removed_count += 1
            continue
            
        filtered_commands.append((operands, operator))

    if removed_count > 0:
        new_content = pikepdf.unparse_content_stream(filtered_commands)
        page.Contents = pdf.make_stream(new_content)
        # print(f"  Page {page_num}: Cleaned {removed_count} items.")
    
    return removed_count

import sys

def main():
    target_gray = False
    if len(sys.argv) > 1 and sys.argv[1] == '--target-gray':
        target_gray = True
        print("⚠️  GRAY TARGET MODE ACTIVE: Will remove gray vectors (0.1-0.95).")
    
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
    
    if not files:
        print("No PDF files found in 'input' folder!")
        sys.exit(10) # Exit 10

    print(f"Found {len(files)} PDFs. Starting Batch Process...")
    
    global_total_removed = 0

    for filename in files:
        filepath = os.path.join(INPUT_DIR, filename)
        print(f"\nProcessing: {filename}")
        
        try:
            pdf = pikepdf.open(filepath, allow_overwriting_input=True)
            total = 0
            for i, p in enumerate(pdf.pages):
                total += process_page(pdf, p, i+1, target_gray=target_gray)
            
            if total > 0:
                out_path = os.path.join(OUTPUT_DIR, filename)
                pdf.save(out_path)
                print(f"  -> Finished! Removed {total} objects. Saved to output.")
                global_total_removed += total
            else:
                # If nothing removed, should we save? Maybe not to save time/space?
                # But for consistency, let's say we don't save if 0 changes.
                print("  -> No objects removed.")
            
        except Exception as e:
            print(f"  -> Failed to process {filename}: {e}")

    # Exit Codes for Auto-Pilot
    if global_total_removed > 0:
        sys.exit(0) # Success
    else:
        sys.exit(10) # Nothing found/removed

if __name__ == "__main__":
    main()
