import pikepdf
import os
import sys
from collections import Counter

# =================CONFIGURATION=================
# Directories
INPUT_DIR = 'input'
OUTPUT_DIR = 'output'

# Initial default list (can be overridden by the Auto Wizard)
WATERMARK_TEXTS = []
REMOVE_OPERATORS = [] 
# ===============================================

def ensure_dirs():
    if not os.path.exists(INPUT_DIR):
        os.makedirs(INPUT_DIR)
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def is_watermark(operands, operator, target_texts):
    """
    Check if the instruction represents a watermark.
    """
    # Check for text showing operators
    if operator in [pikepdf.Operator("Tj"), pikepdf.Operator("'"), pikepdf.Operator('"')]:
        if len(operands) > 0 and isinstance(operands[0], (str, bytes, pikepdf.String)):
            text = str(operands[0])
            for w in target_texts:
                if w in text:
                    return True

    # Check for TJ (array of strings)
    if operator == pikepdf.Operator("TJ"):
        if len(operands) > 0 and isinstance(operands[0], list):
            for item in operands[0]:
                if isinstance(item, (str, bytes, pikepdf.String)):
                    text = str(item)
                    for w in target_texts:
                        if w in text:
                            return True
    
    # Check for general operator removal
    if str(operator) in REMOVE_OPERATORS:
        return True

    return False

def process_page(pdf, page, target_texts):
    """
    Parse content stream and remove matching watermarks.
    """
    try:
        commands = pikepdf.parse_content_stream(page)
    except:
        return

    filtered_commands = []
    
    for operands, operator in commands:
        if is_watermark(operands, operator, target_texts):
            continue # Delete it
        filtered_commands.append((operands, operator))

    new_content = pikepdf.unparse_content_stream(filtered_commands)
    # Correct way to replace content is creating a new stream object using the PDF owner
    page.Contents = pdf.make_stream(new_content)

def process_pdf(input_path, output_path, target_texts):
    print(f"Processing: {os.path.basename(input_path)}")
    try:
        pdf = pikepdf.open(input_path, allow_overwriting_input=True)
        for page in pdf.pages:
            process_page(pdf, page, target_texts)
        pdf.save(output_path)
    except Exception as e:
        print(f"Error: {e}")

def analyze_page_content(page):
    """Extract all text strings AND image names from a page's content stream."""
    items = []
    try:
        commands = pikepdf.parse_content_stream(page)
        for operands, operator in commands:
            # TEXT
            if operator == pikepdf.Operator("Tj") and len(operands) > 0:
                 if isinstance(operands[0], (str, bytes, pikepdf.String)):
                    items.append(str(operands[0]))
            elif operator == pikepdf.Operator("TJ") and len(operands) > 0:
                if isinstance(operands[0], list):
                    for item in operands[0]:
                        if isinstance(item, (str, bytes, pikepdf.String)):
                            items.append(str(item))
            # IMAGES / XOBJECTS
            elif operator == pikepdf.Operator("Do") and len(operands) > 0:
                if isinstance(operands[0], pikepdf.Name):
                    items.append(str(operands[0])) # e.g. /Im1
    except:
        pass
    return items

def ask_ai_for_help(candidates, scan_limit, auto_confirm=False):
    """
    Uses Qwen (Dashscope) to identify the watermark from the list.
    """
    try:
        import dashscope
        from http import HTTPStatus
    except ImportError:
        print("Please run 'pip install dashscope' first, or restart start_mac.command")
        return []

    print("\n--- 🧠 AI Analysis (Tongyi Qianwen) ---")
    
    # Check for API Key
    api_key = os.getenv('DASHSCOPE_API_KEY')
    key_file = ".qwen_key"
    
    if not api_key:
        if os.path.exists(key_file):
            with open(key_file, 'r') as f:
                api_key = f.read().strip()
    
    if not api_key:
        return []

    dashscope.api_key = api_key

    # Prepare prompt with frequency info
    text_list = []
    for i, (text, count) in enumerate(candidates):
        is_obvious = " (HIGH FREQUENCY)" if count >= 10 else ""
        text_list.append(f"{i+1}. [Found {count} times] Content: {text}{is_obvious}")
    candidates_str = "\n".join(text_list)
    
    prompt = f"""
    I have extracted the following content (Text or Image IDs) from a PDF.
    One OR MORE of them is likely a watermark.
    
    Candidates:
    {candidates_str}
    
    Rules:
    1. If an Image ID (starts with /Im...) appears MANY times (e.g. > 10 times in the list), it is likely a Tiled Background Watermark.
    2. If multiple images appear thousands of times, THEY ARE ALL WATERMARKS.
    3. If a text has High Frequency, it is likely a Text Watermark.
    
    Task:
    Identify ALL likely watermark content. 
    Return the text/IDs separated by commas (e.g. "/Im1, /Im5, Confidential").
    If you are unsure, return "None".
    """

    print("Asking Qwen to identify ALL watermarks...")
    try:
        response = dashscope.Generation.call(
            dashscope.Generation.Models.qwen_turbo,
            prompt=prompt
        )
        
        if response.status_code == HTTPStatus.OK:
            ai_answer = response.output.text.strip()
            print(f"\n🤖 AI Report: Found watermarks -> [ {ai_answer} ]")
            
            if ai_answer == "None":
                print("AI was unsure.")
                # Fallback: Remove ALL distinct items that appear heavily (tiled images)
                # If an item appears > scan_limit * 10 times, it's definitely a tile.
                fallback_targets = []
                if candidates:
                    for text, count in candidates:
                         if count > scan_limit * 10:
                             fallback_targets.append(text)
                
                if fallback_targets:
                    print(f"Fallback: These items appear heavily (tiled). Removing ALL: {fallback_targets}")
                    if auto_confirm: return fallback_targets
                return []

            # Parse comma separated list
            targets = [t.strip() for t in ai_answer.split(',')]

            if auto_confirm:
                print("Auto-confirming AI selection...")
                return targets
            
            # Manual confirmation fallback
            confirm = input(f"Remove these {len(targets)} items? (y/n): ").lower()
            if confirm == 'y':
                return targets
            
        else:
            print(f"AI Error: {response.code} - {response.message}")
            
    except Exception as e:
        print(f"Failed to call AI: {e}")

    return []

def auto_detect_wizard(files, force_ai=False):
    """
    Scans the first PDF to find repetitive text OR images.
    """
    print("\n--- Auto-Detecting Watermarks ---")
    
    # Silent scan
    try:
        pdf = pikepdf.open(os.path.join(INPUT_DIR, files[0]))
        page_count = len(pdf.pages)
        scan_limit = min(5, page_count)
        
        string_counts = Counter()
        for i in range(scan_limit):
            items = analyze_page_content(pdf.pages[i])
            for t in items:
                string_counts[t] += 1
        
        # Filter candidates (Top 50 to catch multi-layer tiles)
        candidates = []
        for text, count in string_counts.most_common(60):
            clean_text = text.strip()
            # Allow Images (start with /) OR long text OR short specific text if it appears on every page
            # Heuristic: If count == scan_limit (appears on every page), keep it even if short.
            if clean_text.startswith('/'):
                 candidates.append((text, count))
            elif (len(clean_text) > 2 and not clean_text.isdigit()):
                 candidates.append((text, count))
            elif count >= scan_limit: # Short text appearing on EVERY page (e.g. N¥¡)
                 candidates.append((text, count))
                 
        if not candidates:
            print("No suspicious content found.")
            return []

        # Force AI Mode (Zero Click)
        if force_ai:
            return ask_ai_for_help(candidates, scan_limit, auto_confirm=True)

        # Interactive Mode
        print(f"\nI found {len(candidates)} suspicious items (Text or Images).")
        use_ai = input("Do you want AI to analyze them? (Y/n): ").lower().strip()
        if not use_ai: use_ai = 'y'
        
        if use_ai == 'y':
            ai_results = ask_ai_for_help(candidates, scan_limit)
            if ai_results:
                return ai_results

        # Fallback to interview
        selected_texts = []
        for idx, (text, count) in enumerate(candidates[:20]):
            print(f"\nCandidate #{idx+1}: [ {text} ] (Found {count} times)")
            choice = input("Is this a watermark? (y/n/q): ").lower().strip()
            if choice in ['y', 'yes']:
                selected_texts.append(text)
            elif choice in ['q', 'quit']:
                return selected_texts
        return selected_texts

    except Exception as e:
        print(f"Error during auto-detection: {e}")
        return []

def main():
    print("=== PDF Watermark Remover Skill ===")
    ensure_dirs()
    
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
    if not files:
        print(f"No PDF files found in '{INPUT_DIR}'.")
        return

    targets = []
    
    # Mode 1: Auto Wizard (Interactive)
    if len(sys.argv) == 1 or (len(sys.argv) > 1 and sys.argv[1] == '--wizard'):
        targets = auto_detect_wizard(files)

    # Mode 2: ZERO CLICK AI
    elif len(sys.argv) > 1 and sys.argv[1] == '--auto-ai':
        print("🚀 Starting Fully Automated AI Removal...")
        targets = auto_detect_wizard(files, force_ai=True)
        if not targets:
            print("AI didn't find a confident watermark. Please try Manual Mode.")
            return
            
    # Mode 3: Direct removal
    elif len(sys.argv) > 2 and sys.argv[1] == '--remove':
        # Direct removal mode: python script.py --remove "Text1"
        # Supports multiple arguments as one string or multiple? 
        # Simpler: just take the next arg as the text.
        targets = [sys.argv[2]]
    
    # Mode 4: Manual config
    elif len(sys.argv) > 1 and sys.argv[1] == '--manual':
        targets = WATERMARK_TEXTS

    elif len(sys.argv) > 1 and sys.argv[1] == '--analyze':
        auto_detect_wizard(files)
        return

    if not targets:
        print("No watermarks selected. Exiting.")
        return

    print(f"\nPreparing to remove: {targets}")
    print("Starting Batch Processing...")
    
    for f in files:
        in_path = os.path.join(INPUT_DIR, f)
        out_path = os.path.join(OUTPUT_DIR, f)
        process_pdf(in_path, out_path, targets)
    
    print("\nDone! Check the 'output' folder.")

if __name__ == "__main__":
    main()
