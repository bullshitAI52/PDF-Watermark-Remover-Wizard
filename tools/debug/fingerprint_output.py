import pikepdf
import os

OUTPUT_DIR = 'output'
filename = '初赛 详解.pdf'
filepath = os.path.join(OUTPUT_DIR, filename)

if not os.path.exists(filepath):
    print("Output file not found.")
    exit()

pdf = pikepdf.open(filepath)
page = pdf.pages[1] 
commands = pikepdf.parse_content_stream(page)

print(f"--- Scanning OUTPUT {filename} Page 2 ---")
# limit scan
limit = 2000
for i, (operands, operator) in enumerate(commands):
    if i > limit: break
    op = str(operator)
    
    # Check for the suspicious color
    if op in ['sc', 'scn', 'rg']:
        vals = [float(x) for x in operands]
        print(f"{i}: {op} {vals}")
