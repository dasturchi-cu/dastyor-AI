from backend.services.document_render.context import build_obyektivka_render_context
from backend.services.render_service import render_obyektivka_html

raw = {
    "lang": "uz_lat",
    "fullname": "Test",
    "party": "yo'q",
    "degree": "yo'q",
    "langs": "yo'q",
    "work_experience": [{"f": "2011", "t": "h.v", "fs": "5oktabr", "d": ""}],
}
ctx = build_obyektivka_render_context(raw, watermark=True)
print("party", repr(ctx["party"]))
print("work", ctx["work_experience"])
print("current_year", ctx["current_job_year"])
html = render_obyektivka_html(raw, watermark=True, mask_pii=False)
print("yoq in html", "yo'q" in html)
print("2011", "2011" in html)
print("oktabr", "oktabr" in html)
