import pikepdf
import os

INPUT_DIR = 'input'
OUTPUT_DIR = 'output'
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
if not files:
    print("No files.")
    exit()

print("--- Checking for Annotations ---")
for filename in files:
    in_path = os.path.join(INPUT_DIR, filename)
    out_path = os.path.join(OUTPUT_DIR, filename)
    pdf = pikepdf.open(in_path)
    
    total_annots = 0
    for i, page in enumerate(pdf.pages):
        if '/Annots' in page:
            annots = page.Annots
            count = len(annots)
            if count > 0:
                print(f"File '{filename}' Page {i+1}: Found {count} Annotations.")
                for a in annots:
                    subtype = a.get('/Subtype', 'Unknown')
                    print(f"   - Type: {subtype}")
                
                # Nuke them?
                total_annots += count
                page.Annots = pdf.make_stream(b'') # Clear annots? Or just assign empty array
                # Correct way: del page['/Annots']
                del page['/Annots']

    if total_annots > 0:
        print(f"Removed {total_annots} annotations from {filename}")
        pdf.save(out_path)
    else:
        print(f"No annotations found in {filename}")
