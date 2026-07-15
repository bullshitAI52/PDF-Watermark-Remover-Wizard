import sys
from gui_app.main_v2 import PDFViewerApp

app = PDFViewerApp()
try:
    app._open_pdf("input/sample.pdf") # I need to create a dummy sample.pdf first
    print("Open success")
except Exception as e:
    import traceback
    traceback.print_exc()
