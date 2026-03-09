import re

with open('bot/services/obyektivka_docx.py', encoding='utf-8') as f:
    content = f.read()

old = """    _run(title_p, "MA'LUMOTNOMA", bold=True, size_pt=15.0, color=NAVY_CLR, spacing_pt=4)"""
new = """    _run(title_p, lb['title'], bold=True, size_pt=15.0, color=NAVY_CLR, spacing_pt=4)"""

if old in content:
    content = content.replace(old, new, 1)
    with open('bot/services/obyektivka_docx.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: title replaced")
else:
    # Try to find the exact line
    for i, line in enumerate(content.splitlines(), 1):
        if 'LUMOTNOMA' in line or 'title_p' in line:
            print(f"Line {i}: {repr(line)}")
