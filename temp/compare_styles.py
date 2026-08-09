import json
import sys
from features.obyektivka.ref_style_extract import extract

sys.stdout.reconfigure(encoding="utf-8")

ref = extract("temp/ref_converted.docx")
gen = extract("temp/test_v3.docx")

checks = [
    ("margins", ref["section"], gen["section"]),
    ("rel_cols", ref["tables"][0]["grid_dxa"], gen["tables"][0]["grid_dxa"]),
    ("hdr P0 right_indent", ref["paragraphs"][0].get("right_indent_mm"), gen["paragraphs"][0].get("right_indent_mm")),
    ("hdr P2 align", ref["paragraphs"][2].get("align"), gen["paragraphs"][2].get("align")),
    ("value P7 hanging left", ref["paragraphs"][6 if False else 7].get("left_indent_mm"), None),
]

# find first value row in gen
gen_val = next((p for p in gen["paragraphs"] if "\t" in p["text"] and not ":" in p["text"].split("\t")[0]), None)
ref_val = next((p for p in ref["paragraphs"] if p.get("idx") == 7), None)

print("=== STYLE MATCH ===")
print("margins ref:", ref["section"])
print("margins gen:", gen["section"])
print("rel cols match:", ref["tables"][0]["grid_dxa"] == gen["tables"][0]["grid_dxa"])
print("ref value row indent:", ref_val.get("left_indent_mm") if ref_val else None, ref_val.get("first_line_indent_mm") if ref_val else None)
print("gen value row indent:", gen_val.get("left_indent_mm") if gen_val else None, gen_val.get("first_line_indent_mm") if gen_val else None)

# highlight in ido
for p in gen["paragraphs"]:
    if "nishon" in p.get("text", ""):
        hl = [r.get("color") for r in p.get("runs", [])]
        print("ido value runs:", p["text"][:50], hl)
        break

print("tables ref/gen:", len(ref["tables"]), len(gen["tables"]))
