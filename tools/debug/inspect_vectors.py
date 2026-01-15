import pikepdf
import os

INPUT_DIR = 'input'
files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
if not files:
    print("No files.")
    exit()

filepath = os.path.join(INPUT_DIR, files[0])
print(f"Inspecting Vectors in: {filepath}")

pdf = pikepdf.open(filepath)
page = pdf.pages[0]
commands = pikepdf.parse_content_stream(page)

print("\n--- Graphics State & Path Operations ---")
last_color = "Unset"
for operands, operator in commands:
    op = str(operator)
    
    # Track Color Changes
    # g / G = Gray
    # rg / RG = RGB
    # k / K = CMYK
    # sc / scn = Pattern/Separation
    if op in ['g', 'G']:
        last_color = f"Gray({operands[0]})"
    elif op in ['rg', 'RG']:
        last_color = f"RGB({operands[0]}, {operands[1]}, {operands[2]})"
    elif op in ['k', 'K']:
        last_color = f"CMYK({operands})"
    elif op in ['sc', 'scn', 'SC', 'SCN']:
        last_color = f"Pattern/Special({operands})"

    # Path Painting Operators
    # f = fill, S = stroke, B = both
    if op in ['f', 'f*', 'S', 's', 'B', 'B*', 'b', 'b*']:
        print(f"Path Operation '{op}' using Color: {last_color}")
