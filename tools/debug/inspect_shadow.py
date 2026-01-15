import pikepdf
import os

INPUT_DIR = 'input'
files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
filepath = os.path.join(INPUT_DIR, '初赛 详解.pdf')

print(f"Inspecting Drawing Ops on Page 2 of {os.path.basename(filepath)}")
pdf = pikepdf.open(filepath)
page = pdf.pages[1] 

commands = pikepdf.parse_content_stream(page)

# Track colors
current_fill = "Default"
current_stroke = "Default"
last_fill_op = ""
last_stroke_op = ""

print("--- Drawing Operations Sequence ---")
for i, (operands, operator) in enumerate(commands):
    op = str(operator)
    
    # Track Color
    if op in ['g', 'G', 'rg', 'RG', 'k', 'K', 'sc', 'SC', 'scn', 'SCN']:
        val = str(operands)
        if op.lower() == op: # Fill
            current_fill = f"{op} {val}"
        else:
            current_stroke = f"{op} {val}"
            
    # Track Drawing
    if op in ['f', 'F', 'f*', 'S', 's', 'B', 'B*', 'b', 'b*']:
        print(f"Index {i}: Draw '{op}'")
        print(f"  Current Fill:   {current_fill}")
        print(f"  Current Stroke: {current_stroke}")
