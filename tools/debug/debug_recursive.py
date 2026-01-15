import pikepdf
import os

INPUT_DIR = 'input'
files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
if not files: exit()
filepath = os.path.join(INPUT_DIR, files[0])

print(f"Deep Scanning: {filepath}")
pdf = pikepdf.open(filepath)
page = pdf.pages[0]

visited = set()

def inspect_xobject(name, xobj, depth=0):
    indent = "  " * depth
    if name in visited:
        print(f"{indent}Reference to visited {name}")
        return
    visited.add(name)
    
    subtype = xobj.get('/Subtype')
    print(f"{indent}XObject {name} (Type: {subtype})")
    
    if subtype == '/Form':
        try:
            # 1. Parse content stream
            commands = pikepdf.parse_content_stream(xobj)
            for operands, operator in commands:
                op = str(operator)
                if op == 'Do':
                    sub_name = str(operands[0])
                    print(f"{indent}  -> Calls {sub_name}")
                    
                    # Find the resource definition for this sub-object
                    # It might be in the Top page resources OR in the XObject's own resources
                    if '/Resources' in xobj and '/XObject' in xobj.Resources and sub_name in xobj.Resources.XObject:
                        inspect_xobject(sub_name, xobj.Resources.XObject[sub_name], depth+1)
                    elif '/Resources' in page and '/XObject' in page.Resources and sub_name in page.Resources.XObject:
                         # Fallback to page resources
                         inspect_xobject(sub_name, page.Resources.XObject[sub_name], depth+1)
                         
        except Exception as e:
            print(f"{indent}Error: {e}")

print("--- Root Page Resources ---")
if '/Resources' in page and '/XObject' in page.Resources:
    for name, xobj in page.Resources.XObject.items():
        inspect_xobject(str(name), xobj)
