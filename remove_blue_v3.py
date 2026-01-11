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

print(f"Blue Vector Removal V3: Processing {filename}")

def is_blue_ish(operands, op):
    # 1. Check for specific Pattern Blue (Page 1)
    if len(operands) == 1:
        try:
            val = float(operands[0])
            if 0.49 < val < 0.51: return True
        except: pass

    # 2. Check for RGB Blue (Page 2+)
    # Heuristic: 3 operands, B is largest
    if len(operands) == 3:
        try:
            vals = [float(x) for x in operands]
            r, g, b = vals
            # Page 2 color: 0.55, 0.70, 0.88.
            # B=0.88, R=0.55, G=0.70.
            # B > R and B > G? Yes.
            if b > r and b > g:
                # Also check intensity to avoid removing black/dark grey
                # If b < 0.2 it's too dark?
                if b > 0.3: 
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
                current_fill_blue = False
                current_stroke_blue = False
        
        # 2. Color Ops
        elif op in ['sc', 'scn', 'g', 'rg', 'k']:
            if is_blue_ish(operands, op):
                current_fill_blue = True
            else:
                current_fill_blue = False
        
        elif op in ['SC', 'SCN', 'G', 'RG', 'K']:
            if is_blue_ish(operands, op):
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
            # print(f"  [Page {page_num}] Removing op {op} (Blue state)")
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
