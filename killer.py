import pikepdf
import os
import sys

INPUT_DIR = 'input'
OUTPUT_DIR = 'output'

# The exact Image IDs found in forensics
TARGETS = ['/Im1', '/Im5', '/Im7', '/Im2', '/Im3', '/Im6', '/Im10']

def is_watermark(operands, operator):
    if operator == pikepdf.Operator("Do"):
        if len(operands) > 0 and isinstance(operands[0], pikepdf.Name):
            obj_name = str(operands[0])
            if obj_name in TARGETS:
                return True
    return False

def process_page(pdf, page):
    try:
        commands = pikepdf.parse_content_stream(page)
    except:
        return

    filtered_commands = []
    removed_count = 0
    
    for operands, operator in commands:
        if is_watermark(operands, operator):
            removed_count += 1
            continue 
        filtered_commands.append((operands, operator))

    if removed_count > 0:
        new_content = pikepdf.unparse_content_stream(filtered_commands)
        page.Contents = pdf.make_stream(new_content)
    
    return removed_count

def main():
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
    if not files:
        print("No files.")
        return

    print(f"Killer Mode: Targeting {TARGETS}")
    
    for f in files:
        in_path = os.path.join(INPUT_DIR, f)
        out_path = os.path.join(OUTPUT_DIR, f)
        print(f"Processing {f}...")
        
        try:
            pdf = pikepdf.open(in_path, allow_overwriting_input=True)
            total_removed = 0
            for page in pdf.pages:
                total_removed += process_page(pdf, page)
            
            pdf.save(out_path)
            print(f"  -> Removed {total_removed} items.")
            
        except Exception as e:
            print(f"Error: {e}")

    print("\nDone. Please check the output folder.")

if __name__ == "__main__":
    main()
