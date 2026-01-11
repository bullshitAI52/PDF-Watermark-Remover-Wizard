import pikepdf
import os

INPUT_DIR = 'input'
files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
if not files:
    print("No files found")
    exit()

filepath = os.path.join(INPUT_DIR, files[0])
print(f"Inspecting: {filepath}")

pdf = pikepdf.open(filepath)
page = pdf.pages[0]

print(f"Page contents type: {type(page.Contents)}")
if isinstance(page.Contents, pikepdf.Array):
    print(f"Page has {len(page.Contents)} content streams.")
else:
    print("Page has single content stream.")

print("\n--- Raw Content Stream (First 200 ops) ---")
try:
    commands = pikepdf.parse_content_stream(page)
    for i, (operands, operator) in enumerate(commands):
        print(f"{i}: {operator} {operands}")
        if i > 200: break
except Exception as e:
    print(f"Error parsing: {e}")
