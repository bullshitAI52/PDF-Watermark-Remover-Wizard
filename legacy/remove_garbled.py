import pikepdf
import os

INPUT_DIR = 'input'
OUTPUT_DIR = 'output'
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

from collections import Counter

# Dynamic Scanning Logic
def get_dynamic_targets(pdf_path):
    print(f"Scanning {os.path.basename(pdf_path)} for garbage targets...")
    try:
        pdf = pikepdf.open(pdf_path)
        scan_limit = min(5, len(pdf.pages))
        counts = Counter()
        
        for i in range(scan_limit):
            try:
                commands = pikepdf.parse_content_stream(pdf.pages[i])
                for operands, operator in commands:
                    if operator in [pikepdf.Operator("Tj"), pikepdf.Operator("TJ"), pikepdf.Operator("'"), pikepdf.Operator('"')]:
                        # Extract text item
                        items = []
                        if operator == pikepdf.Operator("TJ"):
                            if len(operands) > 0 and isinstance(operands[0], list):
                                for x in operands[0]: items.append(x)
                        elif len(operands) > 0:
                            items.append(operands[0])
                        
                        for item in items:
                            if isinstance(item, (str, bytes, pikepdf.String)):
                                s = str(item)
                                counts[s] += 1
            except: pass
            
        # Select targets: Appear frequently (>= scan_limit/2) AND look suspicious
        # Suspicious = Starts with < (hex), contains high-ascii, or known patterns
        targets = []
        for text, count in counts.most_common(50):
            # Known patterns or Hex strings
            if text.startswith('<') or 'N¥' in text or '6Å' in text or text.lower() in ['xes', 'xx', 'x', 'e', 's']:
                print(f"  Found Target: {text} (Count: {count})")
                targets.append(text)
            
            # Or purely random short garbage appearing often
            elif count > scan_limit and len(text) < 10:
                 if not text.strip(): continue # Skip whitespace
                 
                 # Be careful not to remove " " or "."
                 clean = text.strip()
                 # Allowlist of safe punctuation to IGNORE (protect)
                 # REMOVED 'x' from safe list based on user feedback
                 safe_chars = ['.', ',', '!', '?', '(', ')', '[', ']', '{', '}', '+', '-', '=', ':', ';', '*', ' ']
                 if clean not in safe_chars and not clean.replace('.','').isdigit():
                      print(f"  Found Target (Freq): {text} (Count: {count})")
                      targets.append(text)
                      
        return targets
    except Exception as e:
        print(f"Scan error: {e}")
        return []

def main():
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
    print(f"Smart Garbage Cleanup Mode")
    
    for f in files:
        in_path = os.path.join(INPUT_DIR, f)
        out_path = os.path.join(OUTPUT_DIR, f)
        
        # Get targets for this specific file
        file_targets = get_dynamic_targets(in_path)
        if not file_targets:
            print(f"  No targets found for {f}. Skipping.")
            continue
            
        print(f"Processing {f} with {len(file_targets)} targets...")
        
        try:
            pdf = pikepdf.open(in_path, allow_overwriting_input=True)
            total_removed = 0
            
            # Helper to check vs dynamic targets
            def is_dynamic_watermark(operands, operator):
                if operator in [pikepdf.Operator("Tj"), pikepdf.Operator("'"), pikepdf.Operator('"')]:
                    if len(operands) > 0 and str(operands[0]) in file_targets: return True
                if operator == pikepdf.Operator("TJ"):
                    if len(operands) > 0 and isinstance(operands[0], list):
                        for item in operands[0]:
                            if str(item) in file_targets: return True
                return False
                
            for page in pdf.pages:
                try:
                    commands = pikepdf.parse_content_stream(page)
                except: continue
                
                filtered_commands = []
                removed_count = 0
                for operands, operator in commands:
                    if is_dynamic_watermark(operands, operator):
                        removed_count += 1
                        continue 
                    filtered_commands.append((operands, operator))

                if removed_count > 0:
                    new_content = pikepdf.unparse_content_stream(filtered_commands)
                    page.Contents = pdf.make_stream(new_content)
                    total_removed += removed_count
            
            pdf.save(out_path)
            print(f"  -> Removed {total_removed} items.")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
