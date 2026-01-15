import pikepdf
import os

INPUT_DIR = 'input'
files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
filename = files[0]
filepath = os.path.join(INPUT_DIR, filename)

pdf = pikepdf.open(filepath)
page = pdf.pages[0]
resources = page.Resources

print(f"--- Color Spaces in {filename} ---")
if '/ColorSpace' in resources:
    cs = resources['/ColorSpace']
    for name, val in cs.items():
        print(f"Name: {name}")
        print(f"  Value: {val}")


print(f"\n--- ExtGState (Transparency) ---")
if '/ExtGState' in resources:
    egs = resources['/ExtGState']
    for name, val in egs.items():
        print(f"State: {name}")
        # Check standard transparency keys
        if '/ca' in val: print(f"  ca (Non-Stroking Alpha): {val['/ca']}")
        if '/CA' in val: print(f"  CA (Stroking Alpha): {val['/CA']}")
        if '/BM' in val: print(f"  BM (Blend Mode): {val['/BM']}")
        if '/SMask' in val: print(f"  SMask (Soft Mask): {val['/SMask']}")


