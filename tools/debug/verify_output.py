import pikepdf
import os

OUTPUT_DIR = 'output'
files = [f for f in os.listdir(OUTPUT_DIR) if f.lower().endswith('.pdf')]
if not files:
    print("No output files found")
    exit()

filename = files[0]
filepath = os.path.join(OUTPUT_DIR, filename)
print(f"Verifying: {filepath}")

pdf = pikepdf.open(filepath)
page = pdf.pages[0]
commands = pikepdf.parse_content_stream(page)

found = False
for operands, operator in commands:
    if str(operator) == 'Do':
        if len(operands) > 0:
            name = str(operands[0])
            if name in ['/KSPX200', '/KSPX199', '/KSPX1', '/KSPX452', '/KSPX476', '/KSPX201', '/KSPX202']:
                found = True
                print(f"❌ FAILURE: {name} is still present!")

if not found:
    print("✅ SUCCESS: Malicious XObjects removed from stream.")
