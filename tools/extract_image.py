import pikepdf
import os
from PIL import Image
import io

INPUT_DIR = 'input'
files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
pdf = pikepdf.open(os.path.join(INPUT_DIR, files[0]))
page = pdf.pages[0]

# Find KSPX1
def find_and_save(resources):
    if '/XObject' not in resources: return False
    
    for name, xobj in resources.XObject.items():
        if str(name) == '/KSPX1':
            print("Found /KSPX1 deep inside!")
            pdfimage = pikepdf.PdfImage(xobj)
            pil_image = pdfimage.as_pil_image()
            pil_image.save("extracted_kspx1.jpg")
            print("Saved to extracted_kspx1.jpg")
            return True
            
        # Recursive check if Form
        if xobj.get('/Subtype') == '/Form' and '/Resources' in xobj:
             if find_and_save(xobj.Resources): return True
             
    return False

# Check top level
if not find_and_save(page.Resources):
    print("Not found anywhere.")
