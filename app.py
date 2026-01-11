import streamlit as st
import os
import time
import subprocess
import shutil

# Page Config
st.set_page_config(
    page_title="PDF Watermark Assistant",
    page_icon="🚀",
    layout="wide"
)

# Constants
INPUT_DIR = 'input'
OUTPUT_DIR = 'output'
IMAGE_INPUT_DIR = 'image_mode_pic_watermark/input'
IMAGE_OUTPUT_DIR = 'image_mode_pic_watermark/output'
KEY_FILE = '.qwen_key'

# --- Helper Functions ---
def save_uploaded_file(uploaded_file, dest_folder):
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    path = os.path.join(dest_folder, uploaded_file.name)
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path

def get_api_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, 'r') as f:
            return f.read().strip()
    return ""

def set_api_key(key):
    with open(KEY_FILE, 'w') as f:
        f.write(key)

# --- UI Layout ---
st.title("🚀 PDF Watermark AI Remover")
st.markdown("Automated cleaning for standard and flattened PDFs.")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # API Key
    current_key = get_api_key()
    new_key = st.text_input("Dashscope API Key", value=current_key, type="password")
    if new_key != current_key:
        set_api_key(new_key)
        st.success("API Key updated!")
    
    st.markdown("---")
    st.markdown("### 📚 Guide")
    st.markdown("1. **Standard Mode**: For normal PDFs (Text/Images).")
    st.markdown("2. **Image Mode**: For scanned/flattened PDFs.")
    st.markdown("3. **Expert Mode**: Stronger scripts.")

# Tabs
tab1, tab2, tab3 = st.tabs(["📄 Standard Cleanup", "🖼️ Image/Scan Mode", "🛠️ Expert Tools"])

# --- TAB 1: Standard ---
with tab1:
    st.header("Standard AI Cleanup")
    st.info("Best for most files. Uses AI to detect and remove watermarks.")
    
    uploaded_files = st.file_uploader("Upload PDFs", type=['pdf'], accept_multiple_files=True, key="std_up")
    
    if st.button("Start Processing 🚀", key="run_std"):
        if not uploaded_files:
            st.warning("Please upload files first.")
        else:
            # 1. Clear Input/Output
            # (Optional: preserve old? usually cleaner to clear for batch)
            # For web app, just overwrite.
            pass
            
            progress = st.progress(0)
            log_box = st.empty()
            
            # Save files
            files_to_process = []
            for f in uploaded_files:
                path = save_uploaded_file(f, INPUT_DIR)
                files_to_process.append(path)
                
            log_box.write("Files uploaded. Initializing AI...")
            progress.progress(20)
            
            # Run Script
            # We run via subprocess to reuse existing logic
            # OR import pdf_watermark_remover directly. Subprocess is safer for env isolation if needed,
            # but direct import gives better feedback. Let's run subprocess to keep it robust.
            
            cmd = [".venv/bin/python", "fix_and_run_ai.command"] # Wait, command is bash.
            # Let's run the python script directly.
            cmd = [".venv/bin/python", "pdf_watermark_remover.py", "--auto-ai"]
            
            try:
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                )
                
                output_log = ""
                for line in process.stdout:
                    output_log += line
                    log_box.code(output_log[-1000:]) # Show last 1000 chars
                
                process.wait()
                progress.progress(100)
                st.success("Processing Complete!")
                
                # Show Downloads
                st.subheader("📥 Download Results")
                for f in os.listdir(OUTPUT_DIR):
                    if f.endswith('.pdf'):
                        path = os.path.join(OUTPUT_DIR, f)
                        with open(path, "rb") as pdf_file:
                            st.download_button(
                                label=f"Download {f}",
                                data=pdf_file,
                                file_name=f"Clean_{f}",
                                mime='application/pdf'
                            )
            except Exception as e:
                st.error(f"Error running script: {e}")

# --- TAB 2: Image Mode ---
with tab2:
    st.header("Image/Scan Cleanup")
    st.warning("Use this only if Standard Mode fails (e.g. text cannot be selected).")
    
    img_files = st.file_uploader("Upload Flattened PDFs", type=['pdf'], accept_multiple_files=True, key="img_up")
    
    if st.button("Start Vision Cleanup 👁️", key="run_img"):
        if not img_files:
            st.warning("Upload files first.")
        else:
            progress2 = st.progress(0)
            log_box2 = st.empty()
            
            for f in img_files:
                save_uploaded_file(f, IMAGE_INPUT_DIR)
            
            log_box2.write("Files ready. Starting Vision Processor...")
            progress2.progress(10)
            
            cmd = [".venv/bin/python", "image_mode_pic_watermark/raster_cleaner.py"]
            
            try:
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                )
                
                output_log = ""
                for line in process.stdout:
                    output_log += line
                    log_box2.code(output_log[-1000:])
                    
                process.wait()
                progress2.progress(100)
                st.success("Vision Processing Complete!")
                
                st.subheader("📥 Download Results")
                for f in os.listdir(IMAGE_OUTPUT_DIR):
                    if f.endswith('.pdf'):
                        path = os.path.join(IMAGE_OUTPUT_DIR, f)
                        with open(path, "rb") as pdf_file:
                            st.download_button(
                                label=f"Download {f}",
                                data=pdf_file,
                                file_name=f"Vision_{f}",
                                mime='application/pdf'
                            )
            except Exception as e:
                st.error(f"Error: {e}")

# --- TAB 3: Expert ---
with tab3:
    st.header("Forensic Tools")
    st.error("⚠️ Expert Mode: These scripts are aggressive.")
    
    expert_files = st.file_uploader("Upload Stubborn PDF", type=['pdf'], key="exp_up")
    
    if expert_files:
         path = save_uploaded_file(expert_files, INPUT_DIR)
         st.write(f"Target: {expert_files.name}")
         
         col1, col2 = st.columns(2)
         with col1:
             if st.button("Run Universal Killer V2 (Black/Validation)"):
                 cmd = [".venv/bin/python", "universal_killer_v2.py"]
                 subprocess.run(cmd)
                 st.success("Killer script executed.")
                 
                 # Check output
                 out_f = os.path.join(OUTPUT_DIR, expert_files.name)
                 if os.path.exists(out_f):
                     with open(out_f, "rb") as f:
                        st.download_button("Download Result", f, file_name=f"Killer_{expert_files.name}")

