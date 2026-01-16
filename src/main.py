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
import json
from collections import Counter
from pikepdf import PdfImage
try:
    from PIL import Image
except ImportError:
    Image = None

# =================CONFIGURATION=================
# Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR, 'input')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

# Initial default list (can be overridden by the Auto Wizard)
WATERMARK_TEXTS = [
    "夏 门 ⼩ 学 学 习 群",
    "门 ⼩ 学 学 习 群",
    "期 末 复 习 打 卡",
    "期 末 复 习 课",
    "期 末 真 题",
    "可 添 加 咨 询 厦 门 郭 ⽼ 师",
    "可 添 加 咨 询 厦 门 郭 ⽼ 师 v x : x n k l x x 2 0 4",
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

def normalize_text(text):
    """
    Removes all whitespace from text to handle spacing issues.
    e.g. "厦 门" -> "厦门"
    """
    if not text: return ""
    return "".join(text.split())

def is_watermark(operands, operator, target_texts):
    """
    Check if the instruction represents a watermark.
    Handles fragmentation (TJ) and spacing (normalization).
    """
    pdf_text = ""
    
    # 1. Extract text from various operators
    if operator in [pikepdf.Operator("Tj"), pikepdf.Operator("'"), pikepdf.Operator('"')]:
        if len(operands) > 0 and isinstance(operands[0], (str, bytes, pikepdf.String)):
            pdf_text = str(operands[0])
            
    elif operator == pikepdf.Operator("TJ"):
        if len(operands) > 0 and isinstance(operands[0], list):
            # Reconstruct full string from chunks
            parts = []
            for item in operands[0]:
                if isinstance(item, (str, bytes, pikepdf.String)):
                    parts.append(str(item))
            pdf_text = "".join(parts)
            
    # 2. Check against targets
    if not pdf_text:
        # semantic check for other operators?
        if str(operator) in REMOVE_OPERATORS:
            return True
        return False
        
    # Standard check
    for w in target_texts:
        if w in pdf_text:
            return True
            
    # Normalized check (ignore spaces)
    norm_pdf = normalize_text(pdf_text)
    for w in target_texts:
        norm_w = normalize_text(w)
        if norm_w and norm_w in norm_pdf:
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

    return str(text)

def scan_xobjects(pdf, target_texts, target_dimensions=None):
    """
    Scans all XObjects.
    - target_texts: list of strings (watermark text inside Form XObject)
    - target_dimensions: set of strings "WxH" (e.g. {"100x200"}) for Image XObjects
    Returns a list of XObject names to be removed.
    """
    bad_xobjects = set()
    print("Scanning XObjects for hidden watermarks...")
    
    try:
        # Iterate over ALL pages
        for page_idx, page in enumerate(pdf.pages):
            if '/Resources' in page and '/XObject' in page.Resources:
                xobjects = page.Resources.XObject
                for name, xobj in xobjects.items():
                    if name in bad_xobjects: continue 
                    
                    # 0. Direct Name Match (User selected this specific object in Wizard)
                    if name in target_texts:
                        print(f"  [Page {page_idx+1}] Found Selected Target Object -> {name}")
                        bad_xobjects.add(name)
                        continue 
                    
                    subtype = xobj.get('/Subtype')
                    
                    # 1. TEXT / FORM Watermark Check
                    if subtype == '/Form':
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
                            
                    # 2. IMAGE Dimension Check
                    elif subtype == '/Image' and target_dimensions:
                        try:
                            # Strict check: Must match BOTH Width and Height
                            w = xobj.get('/Width')
                            h = xobj.get('/Height')
                            if w and h:
                                dim_key = f"{w}x{h}"
                                if dim_key in target_dimensions:
                                    print(f"  [Page {page_idx+1}] Found Image Watermark (Size: {dim_key}) -> {name}")
                                    bad_xobjects.add(name)
                        except:
                            pass
                        
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

def process_pdf(input_path, output_path, target_texts=None, target_dimensions=None):
    print(f"Processing: {os.path.basename(input_path)}")
    try:
        # Defaults
        if target_texts is None: target_texts = []
        if target_dimensions is None: target_dimensions = set()

        pdf = pikepdf.open(input_path, allow_overwriting_input=True)
        
        # Pre-scan for XObjects
        bad_xobjects = scan_xobjects(pdf, target_texts, target_dimensions)
        
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

def extract_page_preview(pdf_path, page_index):
    """
    Renders a specific page of the PDF to a JPEG for context preview.
    Returns: absolute path to image file.
    """
    try:
        from pdf2image import convert_from_path
        
        temp_dir = os.path.join(os.path.dirname(OUTPUT_DIR), "temp_images")
        if not os.path.exists(temp_dir): os.makedirs(temp_dir)
        
        preview_filename = f"context_p{page_index+1}.jpg"
        preview_path = os.path.join(temp_dir, preview_filename)
        
        # Cache check
        if os.path.exists(preview_path):
            return preview_path
            
        # Render
        # usage: convert_from_path(pdf_path, first_page=..., last_page=...)
        # page_index is 0-based, first_page is 1-based
        images = convert_from_path(pdf_path, first_page=page_index+1, last_page=page_index+1, dpi=72)
        if images:
            images[0].save(preview_path)
            return preview_path
            
    except Exception as e:
        # print(f"Preview Render Error: {e}")
        pass
    return None

def render_form_xobject(pdf, xobj, xobj_name):
    """
    Helper: Renders a Form XObject to a clean PDF page and converts to image.
    """
    try:
        from pdf2image import convert_from_path
        
        # 1. Get Dimensions
        bbox = xobj.get('/BBox')
        if not bbox:
            bbox = [0, 0, 1000, 1000] # Fallback
        
        width = float(bbox[2]) - float(bbox[0])
        height = float(bbox[3]) - float(bbox[1])
        
        # 2. Create a temporary PDF with this single page
        # We use a trick: Create a new PDF, copy the logic
        # But simpler: Just use the current PDF context to create a page, then save that page to a temp file.
        
        # Create a blank page in the SAME pdf (to keep resource references valid)
        # Note: We won't save the main PDF, so this is safe.
        temp_page = pdf.add_blank_page(page_size=(width, height))
        
        # Set Resources to include our XObject
        # We need to wrap it properly
        temp_page.Resources = pdf.make_indirect({
            "/XObject": { xobj_name: xobj }
        })
        
        # Draw it: q /Name Do Q
        # Adjust coordinate system if needed, but usually Form XObjects draw at 0,0 of their BBox
        # but the content stream coordinate system might need translation if BBox[0,1] != 0
        content_ops = f"q 1 0 0 1 {-float(bbox[0])} {-float(bbox[1])} cm {xobj_name} Do Q"
        temp_page.Contents = pdf.make_stream(content_ops.encode())
        
        # 3. Export this page to a temp PDF
        temp_pdf_path = os.path.join(os.path.dirname(OUTPUT_DIR), "temp_form_preview.pdf")
        
        # To save just this page, we create a new PDF and copy the page over
        dest_pdf = pikepdf.new()
        dest_pdf.pages.append(temp_page)
        dest_pdf.save(temp_pdf_path)
        dest_pdf.close()
        
        # 4. Render to Image
        images = convert_from_path(temp_pdf_path, dpi=72)
        if images:
            temp_dir = os.path.join(os.path.dirname(OUTPUT_DIR), "temp_images")
            safe_name = xobj_name.replace("/", "").replace(" ", "_")
            preview_filename = f"preview_form_{safe_name}.jpg"
            preview_path = os.path.join(temp_dir, preview_filename)
            images[0].save(preview_path)
            
            # Cleanup
            if os.path.exists(temp_pdf_path): os.remove(temp_pdf_path)
            
            # Remove the temp page from source pdf (in memory) to keep it clean-ish
            # pdf.pages.remove(p=-1) 
            
            return preview_path
            
    except Exception as e:
        print(f"Form Render Error: {e}")
        return None
    return None

def extract_sample_image(pdf, page_index, xobj_name, width=0, height=0):
    """
    Extracts an image XObject from the PDF and saves it as a temp file for preview.
    Returns the absolute path to the preview image.
    """
    try:
        temp_dir = os.path.join(os.path.dirname(OUTPUT_DIR), "temp_images")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        if not Image: return None
        
        page = pdf.pages[page_index]
        if xobj_name not in page.Resources.XObject:
            return None
            
        xobj = page.Resources.XObject[xobj_name]
        
        # Subtype check
        subtype = xobj.get('/Subtype')
        if subtype and str(subtype) == '/Form':
             return render_form_xobject(pdf, xobj, xobj_name)

        # Safe filename
        safe_name = xobj_name.replace("/", "").replace(" ", "_")
        preview_filename = f"preview_p{page_index+1}_{safe_name}_{width}x{height}.jpg"
        preview_path = os.path.join(temp_dir, preview_filename)
        
        if os.path.exists(preview_path):
            return preview_path
            
        # Extract using pikepdf.PdfImage
        try:
            pdfimage = PdfImage(xobj)
            pil_image = pdfimage.as_pil_image()
            
            # Convert to RGB if needed (e.g. CMYK)
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
                
            pil_image.save(preview_path)
            return preview_path
        except Exception as e:
            # Common error: not an image, or unsupported filter
            return None

    except Exception as e:
        return None

def get_image_stats(pdf_path, scan_limit=5):
    """
    Scans a PDF (up to scan_limit pages) for Image XObjects and returns stats.
    Returns: (Counter(dimensions), dict(sample_info))
    sample_info = { "WxH": {'name': '/Im1', 'page': 0} }
    """
    image_stats = Counter()
    image_samples = {}
    
    try:
        pdf = pikepdf.open(pdf_path)
        # scan a few pages or all? For wizard, maybe first 10?
        # If user wants full scan, they use --scan-images
        limit = min(len(pdf.pages), scan_limit)
        
        for i in range(limit):
            page = pdf.pages[i]
            if '/Resources' in page and '/XObject' in page.Resources:
                xobjects = page.Resources.XObject
                for name, xobj in xobjects.items():
                    if xobj.get('/Subtype') == '/Image':
                        try:
                            width = xobj.get('/Width')
                            height = xobj.get('/Height')
                            if width and height:
                                key = f"{width}x{height}"
                                image_stats[key] += 1
                                if key not in image_samples:
                                    image_samples[key] = {'name': str(name), 'page': i}
                        except:
                            pass
    except Exception as e:
        print(f"Image scan error: {e}")
        
    return image_stats, image_samples

def scan_images_in_pdf(pdf_path):
    """
    CLI Wrapper: Scans a PDF and prints report.
    """
    print(f"Scanning images in: {os.path.basename(pdf_path)}")
    try:
        # Full scan for CLI utility
        image_stats, image_samples = get_image_stats(pdf_path, scan_limit=9999)
        
        pdf = pikepdf.open(pdf_path)
        total_pages = len(pdf.pages)
        
        print("\n--- Image Report (Dimensions: count) ---")
        if not image_stats:
            print("No images found.")
        
        sorted_stats = image_stats.most_common()
        for i, (dim, count) in enumerate(sorted_stats):
            info = image_samples[dim]
            sample_name = info['name']
            # Heuristic
            mark = " "
            if count == total_pages: mark = "★ (Every Page)"
            elif count > total_pages * 0.8: mark = "☆ (Most Pages)"
            
            print(f"{i+1}. Size: [{dim}] | Count: {count} {mark} | Sample: {sample_name} (Page {info['page']+1})")
            
        print("\nTip: To remove a specific size, run: python3 src/main.py --remove-image 3978x1923")
        
    except Exception as e:
        print(f"Error scanning images: {e}")

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
    
    prompt = (
        "Analyze this image for watermarks. A watermark is typically:"
        "1. Faint, transparent text overlaid on top of content (often diagonal)."
        "2. Repeated logos or text patterns in the background."
        "3. URLs or 'Scanned by' text in headers/footers.\n\n"
        "If you see a watermark, extract clearly ONLY the text content of the watermark. "
        "Do not describe it, just give me the text. "
        "If there is NO watermark, return the word 'None'."
    )
    
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
    candidate_list_str = "\n".join([f"{i+1}. '{text}' (Freq: {count} - Appears on {count}/{scan_limit} scanned pages)" for i, (text, count) in enumerate(candidates)])
    
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
    I am analyzing a PDF document to remove watermarks. I have extracted some frequently appearing text strings.
    Please help me identify which strings are definitely WATERMARKS that interfere with reading.
    
    Context:
    - The PDF has {scan_limit} pages scanned.
    - If a string appears {scan_limit} times, it is on EVERY page.
    
    Candidates:
    {candidate_list_str}
    
    Instructions:
    1. Identify strings that look like:
       - Promotional text (e.g., "Scan by...", "Created with...", "Paid version")
       - Names of institutions/teachers repeated on every page (e.g., "Teacher Guo", "Xiamen School")
       - Useless headers/footers that serve no educational purpose.
       - URLs or phone numbers.
    2. Do NOT remove:
       - Page numbers (e.g., "1", "2", "- 1 -") UNLESS they are combined with ads.
       - Chapter titles (unless they overlap content).
    3. Return your answer in JSON format:
       {{
           "watermarks": ["text to remove 1", "text to remove 2"],
           "reason": "Brief explanation of why these were chosen"
       }}
    4. If no obvious watermark is found, return {{"watermarks": [], "reason": "None"}}
    """
    
    try:
        response = dashscope.Generation.call(
            model='qwen-plus', # Upgraded to Plus for better logic
            messages=[{'role': 'user', 'content': prompt}],
            result_format='message'
        )
        
        if response.status_code == HTTPStatus.OK:
            content = response.output.choices[0].message.content
            # Cleanup code blocks if present
            if "```json" in content:
                content = content.replace("```json", "").replace("```", "")
            
            print(f"AI Analysis Raw: {content[:100]}...")
            
            try:
                data = json.loads(content)
                suspects = data.get("watermarks", [])
                reason = data.get("reason", "No reason provided")
                print(f"AI Reason: {reason}")
                
                # Double check: ensure suspects are actually in our candidate list
                # (AI might slightly hallucinate or trim text)
                valid_suspects = []
                candidate_texts = [c[0] for c in candidates]
                
                for s in suspects:
                    if s in candidate_texts:
                        valid_suspects.append(s)
                    else:
                        # fuzzy matching or warn?
                        pass
                        
                return valid_suspects
                
            except json.JSONDecodeError:
                print("⚠️ AI return invalid JSON, falling back to text search.")
                # Fallback to old text search method
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

def auto_detect_wizard(files, force_ai=False, heuristic_mode=False):
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
        text_pages = {} # text -> first_page_index
        for i in range(scan_limit):
            items = analyze_page_content(pdf.pages[i])
            for t in items:
                string_counts[t] += 1
                if t not in text_pages:
                    text_pages[t] = i
        
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
            print("No suspicious text found.")
            # Don't return yet, check images too!

        # --- IMAGE CHECK ---
        selected_dimensions = set()
        img_stats, img_samples = get_image_stats(os.path.join(INPUT_DIR, files[0]), scan_limit=scan_limit)
        
        # Filter suspicious images (appearing on > 80% scanned pages)
        suspicious_imgs = []
        for dim, count in img_stats.items():
            if count >= scan_limit * 0.8: # Appears on most pages
                suspicious_imgs.append((dim, count))
        
        # --- BATCH PREVIEW GENERATION ---
        # To avoid lag during the "interview", we pre-render everything now.
        total_items = len(suspicious_imgs) + len(candidates)
        if total_items > 0:
            print(f"\n⏳ Preparing previews for {total_items} candidates... (This might take a moment)")
            
            # Open PDF once for reading
            pdf_for_preview = pikepdf.open(os.path.join(INPUT_DIR, files[0]))
            
            # 1. Images
            img_previews = {} # dim -> path
            for dim, count in suspicious_imgs:
                try:
                    info = img_samples.get(dim)
                    if info:
                        w, h = dim.split('x')
                        path = extract_sample_image(pdf_for_preview, info['page'], info['name'], w, h)
                        if path: img_previews[dim] = path
                except: pass
                
            # 2. Text / Vectors
            text_previews = {} # candidate_index -> path
            candidate_map = {} # candidate_index -> (type, value)
            
            for idx, (text, count) in enumerate(candidates):
                try:
                    # Type A: XObject
                    if text.startswith('/'):
                        target_name = text.strip()
                        # Find page
                        for p_i in range(min(5, len(pdf_for_preview.pages))):
                            p = pdf_for_preview.pages[p_i]
                            if '/Resources' in p and '/XObject' in p.Resources:
                                if target_name in p.Resources.XObject:
                                    xobj = p.Resources.XObject[target_name]
                                    w = xobj.get('/Width', 0)
                                    h = xobj.get('/Height', 0)
                                    path = extract_sample_image(pdf_for_preview, p_i, target_name, w, h)
                                    if path: text_previews[idx] = path
                                    break
                    
                    # Type B: Text
                    elif text in text_pages:
                        page_idx = text_pages[text]
                        path = extract_page_preview(os.path.join(INPUT_DIR, files[0]), page_idx)
                        if path: text_previews[idx] = path
                        
                except Exception as e:
                    # print(e)
                    pass

        # --- INTERACTION ---
        
        # 1. Ask about Images
        if suspicious_imgs:
            print(f"\n📸 Found {len(suspicious_imgs)} suspicious IMAGES found on most pages:")
            
            # Batch Offer
            if len(suspicious_imgs) > 3 and not force_ai and not heuristic_mode:
                batch_choice = input(f"  ?? Found many ({len(suspicious_imgs)}) image types. Remove ALL of them? (y/n): ").lower().strip()
                if batch_choice == 'y':
                    for dim, count in suspicious_imgs:
                         selected_dimensions.add(dim)
                    print(f"     ✅ Marked all {len(suspicious_imgs)} images for removal.")
                    suspicious_imgs = [] 

            for dim, count in suspicious_imgs:
                # Wizard style Prompt
                print(f"  -> Image Size: [{dim}] (Found on {count}/{scan_limit} pages)")
                
                # Show Preview
                if dim in img_previews:
                    print(f"     👁️  Preview: file://{os.path.abspath(img_previews[dim])}")
                
                choice = input(f"  Is this a watermark image? (y/N): ").lower().strip()
                if choice == 'y':
                    selected_dimensions.add(dim)
                    print(f"     ✅ Marked for removal: Image [{dim}]")
        
        # 2. Force AI Mode (Zero Click) -> NOW ALSO SUPPORTS HEURISTIC MODE
        if force_ai:
             return ask_ai_for_help(candidates, scan_limit, auto_confirm=True), selected_dimensions

        # 3. Heuristic Mode (Zero Click, No AI)
        if heuristic_mode:
            print(f"\n🧠 Heuristic Logic: Selecting items appearing on Most pages (Threshold: >=80%)...")
            selected_texts = []
            
            # Text
            for text, count in candidates:
                if count >= scan_limit * 0.8:
                    print(f"  -> Auto-selecting Text: '{text}' (Freq: {count}/{scan_limit})")
                    selected_texts.append(text)
                else:
                    # Debug: Show what was skipped
                    # print(f"  [Skipped Text] '{text}' (Freq: {count}/{scan_limit} - below 80%)")
                    pass
            
            # Images
            for dim, count in suspicious_imgs:
                if count >= scan_limit * 0.8:
                    print(f"  -> Auto-selecting Image: [{dim}] (Freq: {count}/{scan_limit})")
                    selected_dimensions.add(dim)
                else:
                    # print(f"  [Skipped Image] {dim} (Freq: {count}/{scan_limit} - below 80%)")
                    pass
            
            if not selected_texts and not selected_dimensions:
                print(f"  ⚠️  No items met the 80% threshold (Scanned {scan_limit} pages).")
                print("  Tip: Try Mode 2 (Wizard) to manually select from the candidate list.")
            
            return selected_texts, selected_dimensions

        # 4. Interactive Mode (Text)
        selected_texts = []
        if candidates:
            print(f"\n📝 Found {len(candidates)} suspicious TEXT/OBJECT items.")
            
            # Count how many are Objects (start with /)
            obj_candidates = [c for c in candidates if c[0].startswith('/')]
            
            # Batch Offer for Objects
            if len(obj_candidates) > 3:
                 print(f"  👉 Found {len(obj_candidates)} items strictly named XObjects (e.g. /Im... /X...).")
                 batch_choice = input(f"     Do you want to batch remove ALL {len(obj_candidates)} XObjects? (y/n): ").lower().strip()
                 if batch_choice == 'y':
                     for text, count in obj_candidates:
                         selected_texts.append(text)
                     print(f"     ✅ Marked all {len(obj_candidates)} XObjects for removal.")
                     candidates = [c for c in candidates if not c[0].startswith('/')]
            
            # Batch Offer for Remaining Items (Garbage Text / Vectors)
            if len(candidates) > 5:
                 print(f"  👉 Remaining {len(candidates)} items (likely text fragments or unclassified objects).")
                 batch_choice = input(f"     Do you want to batch remove ALL remaining {len(candidates)} items? (y/n): ").lower().strip()
                 if batch_choice == 'y':
                     for text, count in candidates:
                         selected_texts.append(text)
                     print(f"     ✅ Marked all {len(candidates)} remaining items for removal.")
                     candidates = [] # Clear list
            
            for idx, (text, count) in enumerate(candidates[:20]): # Limit to top 20 interactive
                    print(f"\nCandidate #{idx+1}: [ {text} ] (Found {count} times)")
                    
                    if idx in text_previews:
                         print(f"     👁️  Preview: file://{os.path.abspath(text_previews[idx])}")
                    else:
                        if text.startswith('/'):
                             print("     (No preview available - likely a complex vector)")
                        else:
                             print("     (No preview available)")

                    choice = input("Is this a watermark? (y/n/q): ").lower().strip()
                    if choice in ['y', 'yes']:
                        selected_texts.append(text)
                    elif choice in ['q', 'quit']:
                        break
        
        return selected_texts, selected_dimensions

    except Exception as e:
        print(f"Error during auto-detection: {e}")
        return [], set()

def main():
    print("=== PDF Watermark Remover Skill ===")
    ensure_dirs()
    
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
    if not files:
        print(f"No PDF files found in '{INPUT_DIR}'.")
        return

    targets = []
    target_dimensions = set() # Store "WxH" strings
    
    # Mode 0: Utility - Scan Images
    if len(sys.argv) > 1 and sys.argv[1] == '--scan-images':
        print("🔍 Scanning PDF for Images & Dimensions...")
        # Scan the first PDF found
        scan_images_in_pdf(os.path.join(INPUT_DIR, files[0]))
        return

    # Mode 0.5: Remove Image by Size
    if len(sys.argv) > 2 and sys.argv[1] == '--remove-image':
        # python main.py --remove-image 3978x1923
        dim_str = sys.argv[2]
        target_dimensions.add(dim_str)
        print(f"🎯 Target Mode: Removing Images with size [{dim_str}]")
        # We don't need text targets in this mode, but code expects list
    
    # Mode 1: Auto Wizard (Interactive)
    elif len(sys.argv) == 1 or (len(sys.argv) > 1 and sys.argv[1] == '--wizard'):
        targets, dims = auto_detect_wizard(files)
        target_dimensions.update(dims)

    # Mode 2: ZERO CLICK HEURISTIC (Formerly AI)
    elif len(sys.argv) > 1 and sys.argv[1] == '--auto-ai':
        print("🚀 Starting Automatic Heuristic Removal (High Frequency Items)...")
        targets, dims = auto_detect_wizard(files, heuristic_mode=True)
        target_dimensions.update(dims) # Although currently auto-ai only returns dim if I implemented logic there (I did pass empty though)
        
        if not targets and not target_dimensions:
            print("AI didn't find a confident watermark. Please try Manual Mode.")
            sys.exit(10) # Exit code 10: Nothing found

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
        auto_detect_wizard(files) # Analyze mode still prints stuff, return might be ignored
        return

    if not targets and not target_dimensions:
        print("No watermarks selected. Exiting.")
        sys.exit(10) # Ensure we exit with 10 if targets is empty

    print(f"\nPreparing to remove: {targets}")
    print("Starting Batch Processing...")
    
    for f in files:
        in_path = os.path.join(INPUT_DIR, f)
        out_path = os.path.join(OUTPUT_DIR, f)
        process_pdf(in_path, out_path, targets, target_dimensions)
    
    print("\nDone! Check the 'output' folder.")

if __name__ == "__main__":
    main()
