import pikepdf
import os
from decimal import Decimal

INPUT_DIR = 'input'
OUTPUT_DIR = 'output'
filename = '初赛 详解.pdf'
filepath = os.path.join(INPUT_DIR, filename)

if not os.path.exists(filepath):
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
    filepath = os.path.join(INPUT_DIR, files[0])
    filename = files[0]

print(f"Blue Vector Removal V2: Processing {filename}")

def is_blue_val(operands):
    for x in operands:
        try:
            val = float(x)
            if 0.49 < val < 0.51: # Wider tolerance for 0.502
                return True
        except: pass
    return False

def process_page(pdf, page, page_num):
    try:
        commands = pikepdf.parse_content_stream(page)
    except: return 0

    filtered_commands = []
    removed_count = 0
    
    # Graphics State Stack
    # Each item is (fill_is_blue, stroke_is_blue)
    stack = []
    current_fill_blue = False
    current_stroke_blue = False
    
    for operands, operator in commands:
        op = str(operator)
        
        # 1. Stack Ops
        if op == 'q':
            stack.append((current_fill_blue, current_stroke_blue))
        elif op == 'Q':
            if stack:
                current_fill_blue, current_stroke_blue = stack.pop()
            else:
                # Unbalanced Q? Just reset.
                current_fill_blue = False
                current_stroke_blue = False
        
        # 2. Color Ops
        elif op in ['sc', 'scn', 'g', 'rg', 'k']:
            if is_blue_val(operands):
                current_fill_blue = True
            else:
                current_fill_blue = False
        
        elif op in ['SC', 'SCN', 'G', 'RG', 'K']:
            if is_blue_val(operands):
                current_stroke_blue = True
            else:
                current_stroke_blue = False

        # 3. Drawing Ops
        should_remove = False
        
        # Fill Ops
        if op in ['f', 'F', 'f*']:
            if current_fill_blue: should_remove = True
        
        # Stroke Ops
        elif op in ['S', 's']:
            if current_stroke_blue: should_remove = True
            
        # Both Ops
        elif op in ['B', 'B*', 'b', 'b*']:
            if current_fill_blue or current_stroke_blue: should_remove = True

        if should_remove:
            removed_count += 1
            continue
            
        filtered_commands.append((operands, operator))

    if removed_count > 0:
        new_content = pikepdf.unparse_content_stream(filtered_commands)
        page.Contents = pdf.make_stream(new_content)
        print(f"  Page {page_num}: Removed {removed_count} blue paths.")
    
    return removed_count

pdf = pikepdf.open(filepath, allow_overwriting_input=True)
total_removed = 0
for i, page in enumerate(pdf.pages):
    total_removed += process_page(pdf, page, i+1)

out_path = os.path.join(OUTPUT_DIR, filename)
pdf.save(out_path)
print(f"Done. Removed {total_removed} blue vector paths total.")
