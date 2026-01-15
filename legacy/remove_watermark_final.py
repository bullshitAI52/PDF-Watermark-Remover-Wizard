import pikepdf
import os

INPUT_DIR = 'input'
OUTPUT_DIR = 'output'
filename = '初赛 详解.pdf'
filepath = os.path.join(INPUT_DIR, filename)

if not os.path.exists(filepath):
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
    filepath = os.path.join(INPUT_DIR, files[0])
    filename = files[0]

print(f"Final Watermark Removal: Processing {filename}")

def is_target_color(operands, op):
    # 1. Pattern Blue (Page 1) - One Value ~0.502
    if len(operands) == 1:
        try:
            val = float(operands[0])
            if 0.49 < val < 0.51: return True
        except: pass

    # 2. RGB Blue (Page 2+) - Three Values [0.55, 0.70, 0.88]
    if len(operands) == 3:
        try:
            vals = [float(x) for x in operands]
            r, g, b = vals
            # Strict check for the known blue
            if 0.5 < r < 0.6 and 0.65 < g < 0.75 and 0.8 < b < 0.95:
                return True
            # Also generic Blue-ish check (just in case)
            if b > r + 0.1 and b > g + 0.1:
                return True
                
            # 3. The "Shadow" / "Black" Layer - [1, 0, 0]
            # This is technically Red in RGB, or Cyan=100 in CMYK, or Index 1 in Separation.
            # We target it specifically because the watermark uses it.
            if r == 1.0 and g == 0.0 and b == 0.0:
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
    current_fill_target = False
    current_stroke_target = False
    
    for operands, operator in commands:
        op = str(operator)
        
        # 1. Stack Ops
        if op == 'q':
            stack.append((current_fill_target, current_stroke_target))
        elif op == 'Q':
            if stack:
                current_fill_target, current_stroke_target = stack.pop()
            else:
                current_fill_target = False
                current_stroke_target = False
        
        # 2. Color Ops
        elif op in ['sc', 'scn', 'g', 'rg', 'k']:
            if is_target_color(operands, op):
                current_fill_target = True
            else:
                current_fill_target = False
        
        elif op in ['SC', 'SCN', 'G', 'RG', 'K']:
            if is_target_color(operands, op):
                current_stroke_target = True
            else:
                current_stroke_target = False

        # 3. Drawing Ops (Paths ONLY)
        should_remove = False
        
        # Fill Ops
        if op in ['f', 'F', 'f*']:
            if current_fill_target: should_remove = True
        
        # Stroke Ops
        elif op in ['S', 's']:
            if current_stroke_target: should_remove = True
            
        # Both Ops
        elif op in ['B', 'B*', 'b', 'b*']:
            if current_fill_target or current_stroke_target: should_remove = True

        if should_remove:
            removed_count += 1
            continue
            
        filtered_commands.append((operands, operator))

    if removed_count > 0:
        new_content = pikepdf.unparse_content_stream(filtered_commands)
        page.Contents = pdf.make_stream(new_content)
        print(f"  Page {page_num}: Removed {removed_count} vector paths.")
    
    return removed_count

pdf = pikepdf.open(filepath, allow_overwriting_input=True)
total_removed = 0
for i, page in enumerate(pdf.pages):
    total_removed += process_page(pdf, page, i+1)

out_path = os.path.join(OUTPUT_DIR, filename)
pdf.save(out_path)
print(f"Done. Removed {total_removed} paths total.")
