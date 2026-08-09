from pathlib import Path
import re
t = Path(r"D:\proyektlar\hujjatchi_ai_bot\webapp\cv.html").read_text(encoding="utf-8")
print("pay_5000", re.findall(r'"pay_5000":"[^"]{0,40}"', t)[:5])
print("cvPackPicker", "cvPackPicker" in t)
print("ready_export", t.count("ready_export"))
o = Path(r"D:\proyektlar\hujjatchi_ai_bot\webapp\obyektivka.html").read_text(encoding="utf-8")
print("obyPackPicker", "obyPackPicker" in o)
print("oby ready_export", o.count("ready_export"))
