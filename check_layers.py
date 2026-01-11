import pikepdf
import os

INPUT_DIR = 'input'
files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
if not files:
    print("No files.")
    exit()

filepath = os.path.join(INPUT_DIR, files[0])
print(f"Inspecting: {filepath}")
pdf = pikepdf.open(filepath)

# 1. Check for OCGs (Layers)
print("\n--- Optional Content Groups (Layers) ---")
if '/OCProperties' in pdf.Root:
    ocprops = pdf.Root['/OCProperties']
    if '/OCGs' in ocprops:
        ocgs = ocprops['/OCGs']
        if isinstance(ocgs, list):
            print(f"Found {len(ocgs)} Layers:")
            for ocg in ocgs:
                print(f"  Name: {ocg.get('/Name', 'Unnamed')}")
        elif isinstance(ocgs, pikepdf.Array):
             print(f"Found {len(ocgs)} Layers (Array):")
             for ocg in ocgs:
                print(f"  Name: {ocg.get('/Name', 'Unnamed')}")
    else:
        print("OCProperties exists but no OCGs list found.")
else:
    print("No OCGs (Layers) found.")

# 2. Check for Marked Content (Artifacts)
print("\n--- Marked Content Scan (First Page) ---")
page = pdf.pages[0]
commands = pikepdf.parse_content_stream(page)
artifact_count = 0
for operands, operator in commands:
    if operator == pikepdf.Operator("BMC") or operator == pikepdf.Operator("BDC"):
        # Begin Marked Content
        tag = operands[0]
        print(f"Marked Content Tag: {tag}")
        if len(operands) > 1:
            props = operands[1]
            print(f"  Properties: {props}")
            if '/Artifact' in str(props):
                artifact_count += 1

print(f"Total 'Artifact' marked types found: {artifact_count}")
