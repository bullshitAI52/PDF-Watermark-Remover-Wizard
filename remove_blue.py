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

print(f"Blue Vector Removal: Processing {filename}")

def is_blue_val(operands):
    # Check if operands contain the specific 0.502 value
    # Allow small tolerance just in case
    for x in operands:
        try:
            val = float(x)
            if 0.500 < val < 0.505: 
                return True
        except: pass
    return False

def process_page(pdf, page):
    try:
        commands = pikepdf.parse_content_stream(page)
    except: return 0

    filtered_commands = []
    removed_count = 0
    
    # State tracking
    fill_is_blue = False
    stroke_is_blue = False
    
    for operands, operator in commands:
        op = str(operator)
        
        # 1. Track Color Setting
        if op in ['sc', 'scn', 'g', 'rg', 'k']:
            if is_blue_val(operands):
                fill_is_blue = True
            else:
                fill_is_blue = False
                
        if op in ['SC', 'SCN', 'G', 'RG', 'K']:
            if is_blue_val(operands):
                stroke_is_blue = True
            else:
                stroke_is_blue = False

        # 2. Check Drawing Ops
        # Fill Ops
        if op in ['f', 'F', 'f*']:
            if fill_is_blue:
                removed_count += 1
                continue
        
        # Stroke Ops
        if op in ['S', 's']:
            if stroke_is_blue:
                removed_count += 1
                continue
                
        # Both Ops
        if op in ['B', 'B*', 'b', 'b*']:
            if fill_is_blue or stroke_is_blue:
                removed_count += 1
                continue

        filtered_commands.append((operands, operator))

    if removed_count > 0:
        new_content = pikepdf.unparse_content_stream(filtered_commands)
        page.Contents = pdf.make_stream(new_content)
    
    return removed_count

pdf = pikepdf.open(filepath, allow_overwriting_input=True)
total_removed = 0
for page in pdf.pages:
    total_removed += process_page(pdf, page)

out_path = os.path.join(OUTPUT_DIR, filename)
pdf.save(out_path)
print(f"Done. Removed {total_removed} blue vector paths.")
