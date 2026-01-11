import pikepdf
import os
from collections import Counter

INPUT_DIR = 'input'
files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
filepath = os.path.join(INPUT_DIR, '初赛 详解.pdf')

def analyze_page_content(page):
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

pdf = pikepdf.open(filepath)
page_count = len(pdf.pages)
scan_limit = min(5, page_count)

string_counts = Counter()
for i in range(scan_limit):
    items = analyze_page_content(pdf.pages[i])
    for t in items:
        string_counts[t] += 1

print(f"--- Searching for 'x', 'e', 's' ---")
for text, count in string_counts.items():
    if text.lower() in ['x', 'e', 's', 'xes'] or 'xes' in text.lower():
        print(f"Count: {count} | Item: {text}")

print(f"--- Top 100 Candidates ---")
for text, count in string_counts.most_common(100):
    print(f"Count: {count} | Item: {text}")
