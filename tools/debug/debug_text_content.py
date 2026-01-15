import pikepdf
import os

INPUT_DIR = 'input'
files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
if not files:
    print("No files found")
    exit()

filename = files[0]
filepath = os.path.join(INPUT_DIR, filename)

print(f"Inspecting: {filename}")
pdf = pikepdf.open(filepath)
page = pdf.pages[0]

commands = pikepdf.parse_content_stream(page)

print("\n--- DUMPING ALL OPERATORS (Text + Do) ---")
for operands, operator in commands:
    op = str(operator)
    if op in ['Tj', "'", '"', 'TJ', 'Do']:
        print(f"OP: {op} | DATA: {operands}")

print("\n--- CHECKING ANNOTATIONS ---")
if '/Annots' in page:
    print(f"Page has {len(page.Annots)} annotations.")
    for annot in page.Annots:
        print(f"Annot: {annot}")
else:
    print("No Annotations found.")

print("\n--- CHECKING RESOURCES (XObjects) ---")
if '/Resources' in page and '/XObject' in page.Resources:
    xobjects = page.Resources.XObject
    print(f"Found {len(xobjects)} XObjects.")
    for name, xobj in xobjects.items():
        print(f"XObject: {name} | Type: {xobj.get('/Subtype')}")
        # If it's a Form, it might have text
        if xobj.get('/Subtype') == '/Form':
            print(f"  -> Form Content Stream (First 100 chars): {xobj.read_bytes()[:100]}...")

