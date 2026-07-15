import sys
import tkinter as tk
import customtkinter as ctk

# We just try to import main_v2 and see if we can trigger the sync function headless
from gui_app.main_v2 import PDFViewerApp

app = PDFViewerApp()
# Check if buttons are correctly bound
print("Sync bound to:", app._btn_sync.cget("command"))
print("Progress bar exists:", hasattr(app, "_progress_bar"))
