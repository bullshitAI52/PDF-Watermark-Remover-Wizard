import pikepdf
import os
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# PDF Watermark Removal Assistant
# DISCLAIMER: This tool is for PERSONAL STUDY & RESEARCH ONLY.
# STRICTLY PROHIBITED FOR COMMERCIAL USE or ILLEGAL ACTIVITIES.
# The author assumes NO LIABILITY for any misuse of this software.
# 免责声明：本工具仅供个人学习研究，严禁用于商业或非法用途。作者不对任何滥用后果负责。
# -----------------------------------------------------------------------------
import sys
from collections import Counter

# =================CONFIGURATION=================
# Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR, 'input')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

# Initial default list (can be overridden by the Auto Wizard)
WATERMARK_TEXTS = [
    "夏 门 ⼩ 学 学 习 群",
    "期 末 复 习 打 卡",
    "期 末 复 习 课",
    "期 末 真 题",
    "可 添 加 咨 询 厦 门 郭 ⽼ 师",
    "x n k l x x 2 0 4",
    "快乐魔法狮",
    "快乐学习魔法狮"
]
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

def decode_hex_string(text):
    """
    Tries to decode a potential hex string (e.g. <D0A1...>) into readable text.
    Returns the decoded string or the original if failed.
    """
    if not text: return ""
    
    # Check if it looks like hex (even if not wrapped in <>)
    # pikepdf might give us raw bytes or a string
    try:
        bytes_obj = None
        if isinstance(text, bytes):
            bytes_obj = text
        elif isinstance(text, str):
            # purely conservative check
            pass
            
        if bytes_obj:
            # Try GBK first (common for Chinese PDFs)
            try:
                return bytes_obj.decode('gbk')
            except:
                try:
                    return bytes_obj.decode('utf-8')
                except:
                    pass
    except:
        pass
    return str(text)

def scan_xobjects(pdf, target_texts):
    """
    Scans all XObjects in the first page (and potentially others) to find those containing target text.
    Returns a list of XObject names (e.g., '/KSPX200') to be removed.
    """
    bad_xobjects = set()
    print("Scanning XObjects for hidden watermarks...")
    
    try:
        # Iterate over ALL pages to find every instance of the watermark XObject
        # Different pages might use different XObject names for the same content
        for page_idx, page in enumerate(pdf.pages):
            if '/Resources' in page and '/XObject' in page.Resources:
                xobjects = page.Resources.XObject
                for name, xobj in xobjects.items():
                    if name in bad_xobjects: continue # Already found
                    
                    if xobj.get('/Subtype') == '/Form':
                        # Parse the stream of this form
                        try:
                            raw_data = xobj.read_bytes()
                            # 1. Quick Byte Match (GBK Encoded)
                            for t in target_texts:
                                # Normalize: Remove spaces (User input often has spaces: "夏 门" -> "厦门")
                                t_clean = t.replace(" ", "")
                                
                                check_list = [t, t_clean]
                                
                                for txt in check_list:
                                    if not txt: continue
                                    
                                    # Strategy A: Encode to GBK -> Hex String -> Search in Stream
                                    try:
                                        gbk_bytes = txt.encode('gbk')
                                        if gbk_bytes in raw_data:
                                            print(f"  [Page {page_idx+1}] Found '{txt}' in XObject {name} (Raw GBK match)")
                                            bad_xobjects.add(name)
                                            continue

                                        hex_str = gbk_bytes.hex().lower().encode()
                                        if hex_str in raw_data.lower():
                                            print(f"  [Page {page_idx+1}] Found '{txt}' in XObject {name} (GBK Hex match)")
                                            bad_xobjects.add(name)
                                            continue
                                    except: pass
                                    
                                    # Strategy B: UTF-16BE Hex
                                    try:
                                        utf_bytes = txt.encode('utf-16be')
                                        hex_str = utf_bytes.hex().lower().encode()
                                        if hex_str in raw_data.lower():
                                            bad_xobjects.add(name)
                                            continue
                                    except: pass
                                    
                                    # Strategy C: Plain String
                                    if txt.encode() in raw_data:
                                        bad_xobjects.add(name)
                        except Exception as e:
                            print(f"Error scanning XObject {name}: {e}")
                        
    except Exception as e:
        print(f"Global Scan Error: {e}")
        
    # Special Case: Magic Lion Image Wrappers
    # Based on deep analysis, if "快乐魔法狮" (Magic Lion) is in the target list,
    # we should also remove the known image wrappers /KSPX452 and /KSPX476 and /KSPX1
    magic_lion_keywords = ["快乐魔法狮", "快乐学习魔法狮"]
    if any(k in target_texts for k in magic_lion_keywords):
        print("  -> Magic Lion detected. Adding known image wrappers to kill list...")
        bad_xobjects.add('/KSPX452')
        bad_xobjects.add('/KSPX476')
        bad_xobjects.add('/KSPX1')

    print(f"Identified {len(bad_xobjects)} malicious XObjects: {bad_xobjects}")
    return bad_xobjects

def process_page(pdf, page, target_texts, bad_xobjects=None):
    """
    Parse content stream and remove matching watermarks.
    """
    try:
        commands = pikepdf.parse_content_stream(page)
    except:
        return

    filtered_commands = []
    
    for operands, operator in commands:
        op = str(operator)
        
        # 1. Standard Text Removal
        if is_watermark(operands, operator, target_texts):
            continue 
            
        # 2. XObject Removal (The new logic)
        if op == 'Do' and bad_xobjects:
            if len(operands) > 0:
                x_name = str(operands[0]) # e.g. /KSPX200
                if x_name in bad_xobjects:
                    continue # KILL IT
        
        filtered_commands.append((operands, operator))

    new_content = pikepdf.unparse_content_stream(filtered_commands)
    # Correct way to replace content is creating a new stream object using the PDF owner
    page.Contents = pdf.make_stream(new_content)

def process_pdf(input_path, output_path, target_texts):
    print(f"Processing: {os.path.basename(input_path)}")
    try:
        pdf = pikepdf.open(input_path, allow_overwriting_input=True)
        
        # Pre-scan for XObjects
        bad_xobjects = scan_xobjects(pdf, target_texts)
        
        for page in pdf.pages:
            process_page(pdf, page, target_texts, bad_xobjects)
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

    return []

def detect_watermark_vision(pdf_path):
    """
    Uses Qwen-VL (Vision) to visually detect the watermark from the first page.
    """
    print("\n--- 👁️ Vision AI Analysis (Qwen-VL) ---")
    
    # 1. Render First Page
    try:
        from pdf2image import convert_from_path
    except ImportError:
        print("Error: 'pdf2image' not installed. Please run: pip install pdf2image")
        return []

    print("Rendering PDF page for AI vision...")
    try:
        images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=100)
    except Exception as e:
        print(f"Failed to render PDF: {e}")
        return []
    
    if not images:
        print("No images rendered.")
        return []

    # Save to temp file
    temp_img = "temp_vision_check.jpg"
    images[0].save(temp_img)
    
    # 2. Call AI
    import dashscope
    from dashscope import MultiModalConversation
    from http import HTTPStatus
    
    # Check key
    api_key = os.getenv('DASHSCOPE_API_KEY')
    key_file = os.path.join(BASE_DIR, ".qwen_key")
    if not api_key and os.path.exists(key_file):
        with open(key_file, 'r') as f:
            api_key = f.read().strip()
            
    if not api_key:
        print("No API Key found.")
        return []
        
    dashscope.api_key = api_key
    
    prompt = "Look at this page. Is there a watermark (text or repeated pattern)? If yes, extract the watermark text exactly. If no watermark, say 'None'. Return ONLY the text."
    
    messages = [
        {
            "role": "user",
            "content": [
                {"image": f"file://{os.path.abspath(temp_img)}"},
                {"text": prompt}
            ]
        }
    ]
    
    print("Asking Qwen-VL to look at the page...")
    try:
        response = MultiModalConversation.call(model='qwen-vl-max', messages=messages)
        
        # Cleanup temp
        if os.path.exists(temp_img): os.remove(temp_img)
        
        if response.status_code == HTTPStatus.OK:
            content = response.output.choices[0].message.content
            # Handle if content is a list (typical for Multimodal)
            if isinstance(content, list):
                # Extract text parts
                text_parts = [item['text'] for item in content if 'text' in item]
                answer = " ".join(text_parts).strip()
            else:
                answer = str(content).strip()

            print(f"\n🤖 Vision Report: [ {answer} ]")
            
            if "None" in answer or len(answer) < 2:
                 return []
            
            # Heuristic: If answer is long sentence, it might be hallucinating or describing.
            # We assume user wants to delete it.
            return [answer]
        else:
            print(f"AI Error: {response.code} - {response.message}")
            return []
            
    except Exception as e:
        print(f"Vision API Failed: {e}")
        return []

def ask_ai_for_help(candidates, scan_limit, auto_confirm=False):
    """
    Uses AI (Qwen-Turbo) to analyze candidate strings and determine which are likely watermarks.
    """
    print("\n🤖 Asking Qwen AI to identifying watermarks from candidates...")
    
    # 1. Prepare data
    candidate_list_str = "\n".join([f"{i+1}. '{text}' (Freq: {count})" for i, (text, count) in enumerate(candidates)])
    
    # 2. Setup AI
    import dashscope
    from http import HTTPStatus
    
    # Check key
    api_key = os.getenv('DASHSCOPE_API_KEY')
    key_file = os.path.join(BASE_DIR, ".qwen_key") 
    if not api_key and os.path.exists(key_file):
        with open(key_file, 'r') as f:
            api_key = f.read().strip()
            
    if not api_key:
        print("⚠️ No API Key found. Returning high-frequency items as fallback.")
        return [text for text, count in candidates if count >= scan_limit]

    dashscope.api_key = api_key
    
    # Prompt
    prompt = f"""
    I have a list of frequently appearing strings from a PDF. Help me identify which ones are WATERMARKS, SPAM, or Header/Footer noise that should be removed.
    
    Candidates:
    {candidate_list_str}
    
    Instructions:
    - Return a Python list of strings that ARE watermarks.
    - Example return format: ["Watermark1", "Confidential"]
    - If none, return []
    - Be aggressive with obviously spammy text (urls, 'scanned by', etc).
    """
    
    try:
        response = dashscope.Generation.call(
            model='qwen-turbo',
            messages=[{'role': 'user', 'content': prompt}],
            result_format='message'
        )
        
        if response.status_code == HTTPStatus.OK:
            content = response.output.choices[0].message.content
            print(f"AI Analysis: {content}")
            
            # Simple parsing: check which candidate texts are present in the AI's output
            # This avoids complex JSON parsing which might fail
            suspects = []
            for text, _ in candidates:
                if text in content:
                    suspects.append(text)
            
            return suspects
        else:
            print(f"AI Check Failed: {response.code} - {response.message}")
            return [text for text, count in candidates if count >= scan_limit]
            
    except Exception as e:
        print(f"AI Request Error: {e}")
        return [text for text, count in candidates if count >= scan_limit]

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
        print("🚀 Starting Fully Automated AI Removal (Text Analysis)...")
        targets = auto_detect_wizard(files, force_ai=True)
        if not targets:
            print("AI didn't find a confident watermark. Please try Manual Mode.")
            return

    # Mode 2.5: Vision AI
    elif len(sys.argv) > 1 and sys.argv[1] == '--vision':
        print("👁️ Starting Vision AI Removal (Qwen-VL)...")
        # Use first PDF to detect
        targets = detect_watermark_vision(os.path.join(INPUT_DIR, files[0]))
        if targets:
             print(f"Vision Detected: {targets}")
             # Ask for confirmation if not fully convinced? Or just trust it.
             # User said "One request... simple". Let's trust it or confirm.
             # Let's confirm to be safe for now, or just go.
             # If --vision is passed, assume user wants it. 
             pass
        else:
             print("Vision AI return nothing.")
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
