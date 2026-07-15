import sys
import tkinter as tk
import customtkinter as ctk
from gui_app.main_v2 import PDFViewerApp

app = PDFViewerApp()
# Mock doc and objects
class MockDoc:
    page_count = 5
app._doc = MockDoc()

app._marked_objects = [{"type": "text", "bbox": [0,0,10,10], "text": "watermark"}]
class MockEngine:
    def get_page_objects(self, idx, filters):
        return [{"type": "text", "bbox": [0,0,10,10], "text": "watermark"}]
    def _is_match(self, t, o, t_p, t_s):
        return True
app._object_engine = MockEngine()

# We can't test CTkMessagebox easily as it blocks. Let's mock it.
import CTkMessagebox
class MockMsg:
    def get(self):
        return "确认同步"
CTkMessagebox.CTkMessagebox = lambda **kwargs: MockMsg()

app._sync_all_pages()

# Let the after loop run a few times
for i in range(10):
    app.update()
    import time
    time.sleep(0.1)

print("Sync done:", getattr(app, '_sync_done', None))
print("Results:", getattr(app, '_sync_results', None))
print("Stats text:", app._stats_label.cget("text"))
print("Status text:", app._status_label.cget("text"))
