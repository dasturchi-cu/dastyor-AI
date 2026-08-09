# -*- coding: utf-8 -*-
import re
from pathlib import Path

ROOT = Path(r"D:\proyektlar\hujjatchi_ai_bot")

# --- cv.html ---
cv = ROOT / "webapp" / "cv.html"
t = cv.read_text(encoding="utf-8")
t, n1 = re.subn(r'"pay_5000":"[^"]*"', '"pay_5000":"💳 Paket tanlash"', t)
t, n2 = re.subn(
    r'"pay_help":"[^"]*"',
    '"pay_help":"Demo bepul. Toza fayl: 3× 14 999 · 5× 19 999 · 1× 7 999. Bugun to\'lasangiz +1 muqova!"',
    t,
)
# alert line (curly apostrophe variants)
t2, n3 = re.subn(
    r"alert\('💳 Avval to.?lov qiling \(7 999 so.?m\)\.'\);",
    "alert((window.DastyorAI&&window.DastyorAI.needPaymentText)?window.DastyorAI.needPaymentText():'💳 Paket tanlang.');",
    t,
)
print("cv pay_5000", n1, "pay_help", n2, "alert", n3)
cv.write_text(t2, encoding="utf-8")

# --- obyektivka.html ---
oby = ROOT / "webapp" / "obyektivka.html"
o = oby.read_text(encoding="utf-8")
o = o.replace(
    '<span id="btn_pay_5000">💳 7 999 so\'m to\'lash</span>',
    '<span id="btn_pay_5000">💳 Paket tanlash</span>',
)
o = o.replace(
    '<div style="font-size:13px;font-weight:800;color:#166534;margin-bottom:8px;">💳 To\'lov (7 999 so\'m)</div>',
    '<div id="obyPayTitle" style="font-size:13px;font-weight:800;color:#166534;margin-bottom:8px;">💳 Paket tanlash</div>\n'
    '        <div id="obyPackPicker"></div>',
)
o = o.replace(
    '<button type="button" class="btn btn-outline hidden" onclick="payObySingle(\'word\')" id="btn_voice_pay">💳 To\'lov (7 999)</button>',
    '<button type="button" class="btn btn-outline hidden" onclick="payObySingle(\'word\')" id="btn_voice_pay">💳 Paket tanlash</button>',
)
o = o.replace(
    'ui_pay_5000:"💳 7 999 so\'m to\'lash",',
    'ui_pay_5000:"💳 Paket tanlash",',
)
o = o.replace(
    'ui_pay_help:"Limit tugasa alohida to\'lov tugmasi orqali davom etasiz (7 999 so\'m = 1 hujjat).",',
    'ui_pay_help:"Demo bepul. Toza fayl: 3× 14 999 · 5× 19 999 · 1× 7 999.",',
)
o2, n4 = re.subn(
    r'warn\.textContent = "🔒 Pul yetarli emas\. Avval to\'lov qiling \(7 999 so\'m = 1 ta hujjat\)\.";',
    'warn.textContent = (DA.needPaymentText ? DA.needPaymentText(u) : "🔒 Pul yetarli emas. Paket tanlang.");',
    o,
)
o3, n5 = re.subn(
    r"alert\('💳 Avval to.?lov qiling \(7 999 so.?m\)\.'\);",
    "alert((window.DastyorAI&&window.DastyorAI.needPaymentText)?window.DastyorAI.needPaymentText():'💳 Paket tanlang.');",
    o2,
)
print("oby warn", n4, "alert", n5)
oby.write_text(o3, encoding="utf-8")

# --- locales ---
uz = ROOT / "webapp" / "locales" / "uz.json"
u = uz.read_text(encoding="utf-8")
u = u.replace(
    '"pay_5000": "💳 7 999 so\'m to\'lash"',
    '"pay_5000": "💳 Paket tanlash"',
)
u = u.replace(
    '"pay_help": "Limit tugasa pastdagi \'7 999 so\'m to\'lash\' tugmasi orqali davom etasiz."',
    '"pay_help": "Demo bepul. Toza fayl: 3× 14 999 · 5× 19 999 · 1× 7 999. Bugun to\'lasangiz +1 muqova bonus!"',
)
u = u.replace(
    '"oby_pay_title": "To\'lov (7 999 so\'m)"',
    '"oby_pay_title": "Paket tanlash"',
)
uz.write_text(u, encoding="utf-8")
print("locales ok")
