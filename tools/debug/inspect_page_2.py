import pikepdf
import os

INPUT_DIR = 'input'
files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
filepath = os.path.join(INPUT_DIR, '初赛 详解.pdf')

print(f"Inspecting Page 2 of {os.path.basename(filepath)}")
pdf = pikepdf.open(filepath)
page = pdf.pages[1] # Page 2

print("\n--- Content Stream Ops (First 50) ---")
try:
    commands = pikepdf.parse_content_stream(page)
    for i, (operands, operator) in enumerate(commands):
        op = str(operator)
        print(f"{i}: {op} {operands}")
        if i > 50: break
        
        # Check for Do
        if op == 'Do':
            print(f"  -> EXECUTE XObject: {operands}")
            # Try to peek into it
            try:
                xobjs = page.Resources['/XObject']
                xname = operands[0]
                if xname in xobjs:
                    xobj = xobjs[xname]
                    subtype = xobj.get('/Subtype', '/Unknown')
                    print(f"     Subtype: {subtype}")
                    # If Form, check its color?
            except: pass

except Exception as e:
    print(f"Error: {e}")
