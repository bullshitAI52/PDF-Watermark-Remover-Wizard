import pikepdf
import os

INPUT_DIR = 'input'
files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
filepath = os.path.join(INPUT_DIR, '初赛 详解.pdf')

pdf = pikepdf.open(filepath)
page = pdf.pages[1] 

print(f"Resources for Page 2 of {os.path.basename(filepath)}")
if '/ColorSpace' in page.Resources:
    cs = page.Resources['/ColorSpace']
    for key, val in cs.items():
        print(f"  {key}: {val}")
else:
    print("  No /ColorSpace resources found on this page.")
