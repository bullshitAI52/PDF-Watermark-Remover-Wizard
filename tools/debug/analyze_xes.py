import pikepdf
import os

INPUT_DIR = 'input'
# Targeting the second file specifically
filename = '初赛 详解.pdf'
filepath = os.path.join(INPUT_DIR, filename)

if not os.path.exists(filepath):
    # Fallback if file was moved to 'done' or just searching inputs
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
    if not files: 
        print("No files found.")
        exit()
    filepath = os.path.join(INPUT_DIR, files[0])
    filename = files[0]

print(f"Analyzing Colors in: {filename}")
pdf = pikepdf.open(filepath)
page = pdf.pages[0]

commands = pikepdf.parse_content_stream(page)

print("\n--- Objects with Color Info ---")
current_color = "Default"
current_color_space = "Default"

def is_blueISH(operands, space):
    # Heuristic for Blue
    try:
        vals = [float(x) for x in operands]
        if space in ['rg', 'RG']: # RGB
            r, g, b = vals
            return b > 0.5 and b > (r + g)
        if space in ['k', 'K']: # CMYK (Blue is Cyan + Magenta)
            c, m, y, k = vals
            return (c > 0.5 or m > 0.5) and y < 0.5
    except: pass
    return False

for operands, operator in commands:
    op = str(operator)
    
    # 1. Track Colors
    if op in ['rg', 'RG']:
        current_color = f"RGB{operands}"
        current_color_space = op
        if is_blueISH(operands, op): print(f"Set BLUE Color (RGB): {operands}")
        
    elif op in ['k', 'K']:
        current_color = f"CMYK{operands}"
        current_color_space = op
        if is_blueISH(operands, op): print(f"Set BLUE Color (CMYK): {operands}")
        
    elif op in ['g', 'G']:
        current_color = f"Gray{operands}"
        current_color_space = op
    
    elif op in ['sc', 'scn', 'SC', 'SCN']:
        current_color = f"Pattern/Spot{operands}"
        current_color_space = op

    # 2. Check Text
    if op in ['Tj', 'TJ', "'", '"']:
        text = ""
        if len(operands) > 0:
             if isinstance(operands[0], (str, bytes, pikepdf.String)): 
                 text = str(operands[0])
             elif isinstance(operands[0], list):
                 text = str(operands[0])
        
        # Only print if it looks suspicious or is using a "Pattern" color
        if "Pattern" in current_color or "Blue" in current_color or "RGB" in current_color:
             print(f"Text '{text}' drawn with Color: {current_color}")
        elif text.lower() in ['x', 'e', 's', 'xes']:
             print(f"Text '{text}' found with Color: {current_color}")

    # 3. Check Paths (f=fill, S=stroke)
    if op in ['f', 'f*', 'F', 'S', 's', 'B', 'B*', 'b', 'b*']:
        if "Pattern" in current_color or "RGB" in current_color or "CMYK" in current_color:
             print(f"Path Operation '{op}' with Color: {current_color}")
