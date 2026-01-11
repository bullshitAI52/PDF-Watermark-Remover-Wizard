import pikepdf
import os

INPUT_DIR = 'input'
files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
filepath = os.path.join(INPUT_DIR, '初赛 详解.pdf')

pdf = pikepdf.open(filepath)
page = pdf.pages[1] 
commands = pikepdf.parse_content_stream(page)

print("--- Scanning for Color/Draw Sequences ---")
# limit scan
limit = 2000
for i, (operands, operator) in enumerate(commands):
    if i > limit: break
    op = str(operator)
    
    # Print only relevant structural text
    # Color, Draw, Save/Restore
    if op in ['q', 'Q', 'cs', 'CS', 'sc', 'SC', 'scn', 'SCN', 'g', 'G', 'rg', 'RG', 'k', 'K', 'f', 'F', 'f*', 'S', 's', 'B', 'B*', 'b', 'b*']:
        print(f"{i}: {op} {operands}")
