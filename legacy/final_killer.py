import pikepdf
import os

INPUT_DIR = 'input'
OUTPUT_DIR = 'output'
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

# TARGETS from the debug dump
# Both Images AND Text
TARGETS = [
    # Top Frequency Images (Tiles)
    '/Im5', '/Im15', '/Im27', '/Im7', '/Im17', '/Im29', '/Im1', 
    '/Im9', '/Im23', '/Im6', '/Im16', '/Im28', '/Im10', 
    '/Im20', '/Im32', '/Im2', '/Im12', '/Im24', '/Im3', '/Im13', '/Im25',
    
    # Text Candidates (Found 3 times = 1 per page)
    "N¥¡", "N¥", "6Å" 
]

def is_watermark(operands, operator):
    # Check Images (Do)
    if operator == pikepdf.Operator("Do"):
        if len(operands) > 0 and isinstance(operands[0], pikepdf.Name):
            if str(operands[0]) in TARGETS:
                return True
    
    # Check Text (Tj, TJ, ', ")
    if operator in [pikepdf.Operator("Tj"), pikepdf.Operator("'"), pikepdf.Operator('"')]:
        if len(operands) > 0 and isinstance(operands[0], (str, bytes, pikepdf.String)):
            text = str(operands[0])
            for t in TARGETS:
                if t in text: return True

    if operator == pikepdf.Operator("TJ"):
        if len(operands) > 0 and isinstance(operands[0], list):
            for item in operands[0]:
                if isinstance(item, (str, bytes, pikepdf.String)):
                    text = str(item)
                    for t in TARGETS:
                        if t in text: return True
    return False

def process_page(pdf, page):
    try:
        commands = pikepdf.parse_content_stream(page)
    except:
        return 0

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
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
    print(f"Final Killer Mode: Targeting {len(TARGETS)} items (Images + Text)")
    
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
            print(f"  -> Removed {total_removed} combined items.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
