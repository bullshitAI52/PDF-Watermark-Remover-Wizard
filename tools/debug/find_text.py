import pikepdf
import os

def find_text_in_pdf(pdf_path, target_text_parts):
    print(f"Scanning {os.path.basename(pdf_path)}...")
    pdf = pikepdf.open(pdf_path)
    
    found_count = 0
    
    for i, page in enumerate(pdf.pages):
        try:
            commands = pikepdf.parse_content_stream(page)
            for operands, operator in commands:
                if operator in [pikepdf.Operator("Tj"), pikepdf.Operator("TJ")]:
                    # Extract text content
                    text_content = ""
                    if operator == pikepdf.Operator("Tj"):
                         if len(operands) > 0: text_content = str(operands[0])
                    elif operator == pikepdf.Operator("TJ"):
                         if len(operands) > 0 and isinstance(operands[0], list):
                             for item in operands[0]:
                                 if isinstance(item, (str, bytes, pikepdf.String)):
                                     text_content += str(item)
                    
                    # Check for matches
                    for part in target_text_parts:
                        if part in text_content:
                            print(f"  ✅ Match Found on Page {i+1}: '{text_content}'")
                            found_count += 1
        except:
            pass
            
    if found_count == 0:
        print("  ❌ No matches found searching for text objects.")
    else:
        print(f"  ✨ Found {found_count} total text matches.")

if __name__ == "__main__":
    INPUT_DIR = 'input'
    # Updated targets based on user screenshot
    targets = ["郭老师", "kxx666222", "Mufasa", "快乐学习", "更多资料"] 
    
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
    for f in files:
        find_text_in_pdf(os.path.join(INPUT_DIR, f), targets)
