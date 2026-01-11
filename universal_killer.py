# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# DISCLAIMER: This tool is for PERSONAL STUDY & RESEARCH ONLY.
# STRICTLY PROHIBITED FOR COMMERCIAL USE or ILLEGAL ACTIVITIES.
# The author assumes NO LIABILITY for any misuse of this software.
# 免责声明：本工具仅供个人学习研究，严禁用于商业或非法用途。作者不对任何滥用后果负责。
# -----------------------------------------------------------------------------
import pikepdf
import os

INPUT_DIR = 'input'
OUTPUT_DIR = 'output'
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

filename = '初赛 详解.pdf'
filepath = os.path.join(INPUT_DIR, filename)

if not os.path.exists(filepath):
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
    if files:
        filepath = os.path.join(INPUT_DIR, files[0])
        filename = files[0]
    else:
        print("Input file not found!")
        exit()

print(f"Universal Killer: Processing {filename}")

def is_garbage_color(operands):
    # Flatten operands to floats
    try:
        vals = [float(x) for x in operands]
    except:
        return False
        
    # 1. Single Value (Grayscale or Pattern)
    if len(vals) == 1:
        v = vals[0]
        # Pattern Blue (0.502)
        if 0.49 <= v <= 0.51:
            return True
        # Maybe purely Black (0.0)? NO, text is black. Don't remove 0.0.

    # 3. RBG / Lab (3 Values)
    elif len(vals) == 3:
        v1, v2, v3 = vals
        # RGB Blue (Page 2+): 0.55, 0.70, 0.88
        # Heuristic: Blue is dominant
        if v3 > v1 and v3 > v2:
             if v3 > 0.8: return True # Bright Blue
             if v3 > 0.4 and v3 < 0.6: return True # Pattern Blue in RGB?
             
        # "Shadow" Layer: Red (1, 0, 0)
        # Note: In the Separation space /Cs1, 1.0 might mean "Full Tint" of the Spot Color.
        # If the Spot Color looks black, then this is it.
        if v1 > 0.9 and v2 < 0.1 and v3 < 0.1:
            return True
            
    # 4. CMYK (4 Values)
    elif len(vals) == 4:
        c, m, y, k = vals
        # If any Cyan/Magenta dominant
        if (c > 0.5 or m > 0.5) and y < 0.5 and k < 0.5:
            return True
            
    return False

def process_page(pdf, page, page_num):
    try:
        commands = pikepdf.parse_content_stream(page)
    except: return 0

    filtered_commands = []
    removed_count = 0
    
    # Global state tracking (simplified, assumes simple q/Q nesting or flat)
    # We'll just check the color state at the moment of 'f' or 'S'
    
    stack = []
    # State: (fill_bad, stroke_bad)
    current_fill_bad = False
    current_stroke_bad = False
    
    for operands, operator in commands:
        op = str(operator)
        
        # Stack
        if op == 'q':
            stack.append((current_fill_bad, current_stroke_bad))
        elif op == 'Q':
            if stack:
                current_fill_bad, current_stroke_bad = stack.pop()
            else:
                current_fill_bad = False
                current_stroke_bad = False
                
        # Colors
        elif op in ['sc', 'scn', 'g', 'rg', 'k']: # Fill
            current_fill_bad = is_garbage_color(operands)
            
        elif op in ['SC', 'SCN', 'G', 'RG', 'K']: # Stroke
            current_stroke_bad = is_garbage_color(operands)
            
        # Draw - Remove if bad color is active
        should_remove = False
        
        if op in ['f', 'F', 'f*']:
            if current_fill_bad: should_remove = True
            
        elif op in ['S', 's']:
            if current_stroke_bad: should_remove = True
            
        elif op in ['B', 'B*', 'b', 'b*']:
            if current_fill_bad or current_stroke_bad: should_remove = True
            
        if should_remove:
            removed_count += 1
            continue
            
        filtered_commands.append((operands, operator))

    if removed_count > 0:
        new_content = pikepdf.unparse_content_stream(filtered_commands)
        page.Contents = pdf.make_stream(new_content)
        print(f"  Page {page_num}: Cleaned {removed_count} items.")
    
    return removed_count

pdf = pikepdf.open(filepath, allow_overwriting_input=True)
total = 0
for i, p in enumerate(pdf.pages):
    total += process_page(pdf, p, i+1)

out_path = os.path.join(OUTPUT_DIR, filename)
pdf.save(out_path)
print(f"Finished. Total objects removed: {total}")
