import pikepdf
import collections

def analyze_colors(pdf_path):
    print(f"Analyzing colors in: {pdf_path}")
    pdf = pikepdf.open(pdf_path)
    
    # Store all color operations
    rgb_stats = collections.Counter()
    cmyk_stats = collections.Counter()

    def scan_stream(content_stream, depth=0):
        try:
            commands = pikepdf.parse_content_stream(content_stream)
            for operands, operator in commands:
                op = str(operator)
                
                # RGB
                if op in ['rg', 'RG', 'sc', 'SC'] and len(operands) == 3:
                    try:
                        vals = tuple([round(float(x), 2) for x in operands])
                        rgb_stats[vals] += 1
                        # print(f"Found RGB: {vals}")
                    except: pass
                    
                # CMYK
                elif op in ['k', 'K'] and len(operands) == 4:
                    try:
                        vals = tuple([round(float(x), 2) for x in operands])
                        cmyk_stats[vals] += 1
                        # print(f"Found CMYK: {vals}")
                    except: pass

                # Recurse into XObjects
                elif op == 'Do' and len(operands) == 1:
                    # We can't easily recurse without the page resources context
                    # But often watermarks are just images here
                    pass
        except: pass

    for i, page in enumerate(pdf.pages[:3]): # Scan first 3 pages
        print(f"Scanning Page {i+1}...")
        # Direct content
        scan_stream(page)
        
        # Check XObject Resources
        if '/Resources' in page and '/XObject' in page['/Resources']:
            xobjects = page['/Resources']['/XObject']
            for name, xobj in xobjects.items():
                # print(f"  Checking XObject: {name}")
                if '/Subtype' in xobj and xobj['/Subtype'] == '/Form':
                    # Form XObjects have content streams
                    print(f"    --> Found Form XObject: {name}, scanning content...")
                    scan_stream(xobj)
            
    print("\n--- Top RGB Colors (Red, Green, Blue) ---")
    for color, count in rgb_stats.most_common(20):
        print(f"Count: {count} | RGB: {color}")
        # Hint likely colors
        r, g, b = color
        if g > r and g > b: print(f"  -> Likely GREEN! 🟢")
        elif b > 0.8 and r < 0.5: print(f"  -> Likely BLUE 🔵")

    print("\n--- Top CMYK Colors (Cyan, Magenta, Yellow, Black) ---")
    for color, count in cmyk_stats.most_common(20):
        print(f"Count: {count} | CMYK: {color}")
        c, m, y, k = color
        if c > 0.3 and y > 0.3: print(f"  -> Likely GREEN/CYAN 🟢")

if __name__ == "__main__":
    import os
    input_dir = 'input'
    files = [f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')]
    if files:
        analyze_colors(os.path.join(input_dir, files[0]))
    else:
        print("No PDF found in input/")
