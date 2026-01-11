import pikepdf
import os
import sys

INPUT_DIR = 'input'
files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
if not files:
    print("No files.")
    sys.exit()

filename = files[0]
filepath = os.path.join(INPUT_DIR, filename)
print(f"Analyzing: {filename}")

pdf = pikepdf.open(filepath)
page = pdf.pages[0]

print(f"\n--- Page Resources ---")
resources = page.Resources
if '/XObject' in resources:
    xobjects = resources['/XObject']
    print(f"Found {len(xobjects)} XObjects:")
    for name, xobj in xobjects.items():
        type_str = str(xobj.get('/Subtype', 'Unknown'))
        print(f"  {name}: {type_str}")
        
        # If it's a Form, let's peek inside
        if type_str == '/Form':
            print(f"    [Form Content] Analyzing stream inside {name}...")
            try:
                form_commands = pikepdf.parse_content_stream(xobj)
                ops = [str(op) for _, op in form_commands]
                print(f"    Ops: {ops[:10]}... (Total {len(ops)})")
                # Check for text in form
                for operands, operator in form_commands:
                    if operator == pikepdf.Operator("Tj"):
                        print(f"    Found Text in Form: {operands}")
            except Exception as e:
                print(f"    Error parsing form: {e}")

print(f"\n--- Main Content Stream Stats ---")
commands = pikepdf.parse_content_stream(page)
op_counts = {}
for operands, operator in commands:
    op = str(operator)
    op_counts[op] = op_counts.get(op, 0) + 1

print("Operator Counts:")
for op, count in sorted(op_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"  {op}: {count}")

print(f"\n--- 'Do' Operator Analysis (Images/Forms) ---")
do_targets = {}
for operands, operator in commands:
    if operator == pikepdf.Operator("Do"):
        name = str(operands[0])
        do_targets[name] = do_targets.get(name, 0) + 1

for name, count in do_targets.items():
    print(f"  Drawn Object '{name}' appears {count} times.")
