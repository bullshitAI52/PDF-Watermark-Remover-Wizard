import fitz
doc = fitz.open()
doc.new_page()
doc.save("test_dummy.pdf")
doc.close()

from gui_app.main_v2 import PDFViewerApp
app = PDFViewerApp()
app._open_pdf("test_dummy.pdf")
print("PDF loaded, page count:", app._doc.page_count)
print("Status:", app._status_label.cget("text"))
