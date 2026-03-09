"""
Rebuild cv_template.html and obyektivka_template.html so they are
pixel-perfect identical to the browser preview in cv.html / obyektivka.html.

Strategy:
  1. Extract the exact <style> block from cv.html (lines 44-648).
  2. Remove browser-only rules (media print hide, box-shadow, margin-bottom).
  3. Add @page { size:A4; margin:0 }.
  4. Write a complete Jinja2 template with the EXACT same HTML structure
     that updateCV() builds in the browser.
"""

import re

# ──────────────────────────────────────────────────────────────────────────────
#  PART 1  — cv_template.html
# ──────────────────────────────────────────────────────────────────────────────
with open("webapp/cv.html", "r", encoding="utf-8") as f:
    src = f.read().replace("\r\n", "\n")

# Extract the CSS block (first <style>...</style>)
m = re.search(r"<style>(.*?)</style>", src, re.DOTALL)
css_raw = m.group(1)

# Strip browser-only noise
css_raw = re.sub(r"@media print\s*\{.*?\}", "", css_raw, flags=re.DOTALL)
css_raw = css_raw.replace("box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);", "")
css_raw = css_raw.replace("margin-bottom: 30px;", "margin: 0;")
# Remove scrollbar / overscroll rules (not needed in PDF)
css_raw = re.sub(r"body\s*\{\s*overscroll-behavior-y:\s*none;\s*\}", "", css_raw)
css_raw = re.sub(r"\.scroller.*?\}", "", css_raw, flags=re.DOTALL)
css_raw = re.sub(r"\.cv-canvas-wrapper.*?\}", "", css_raw, flags=re.DOTALL)

css_raw += """
    @page { size: A4; margin: 0; }
"""

CV_TEMPLATE = """<!DOCTYPE html>
<html lang="uz">
<head>
  <meta charset="UTF-8">
  <title>CV | DASTYOR AI</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@400;600;700;800&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', sans-serif;
      background: #fff;
      color: #1e293b;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }
""" + css_raw + """
  </style>
</head>
<body>
{%- set d = data -%}
{%- set tpl = d.template | default('minimal') -%}

{#── REUSABLE MACROS ────────────────────────────────────────────────────────#}
{%- macro expBlock() -%}
  {%- if d.experiences -%}
  <div class="section">
    <div class="sec-title">Ish tajribasi</div>
    {%- for e in d.experiences -%}
    <div class="item-row">
      <div class="item-head">
        <span class="item-title">{{ e.title }}</span>
        <span class="item-date">{{ e.date }}</span>
      </div>
      {%- if e.company -%}<div class="item-sub">{{ e.company }}</div>{%- endif -%}
      {%- if e.desc -%}<div class="item-desc">{{ e.desc | replace('\\n','<br>') | safe }}</div>{%- endif -%}
    </div>
    {%- endfor -%}
  </div>
  {%- endif -%}
{%- endmacro -%}

{%- macro eduBlock() -%}
  {%- if d.education -%}
  <div class="section">
    <div class="sec-title">Ta'lim</div>
    {%- for e in d.education -%}
    <div class="item-row">
      <div class="item-head">
        <span class="item-title">{{ e.title }}</span>
        <span class="item-date">{{ e.date }}</span>
      </div>
      {%- if e.company -%}<div class="item-sub">{{ e.company }}</div>{%- endif -%}
    </div>
    {%- endfor -%}
  </div>
  {%- endif -%}
{%- endmacro -%}

{%- macro skillsBlock() -%}
  {%- if d.skills -%}
  <div class="section">
    <div class="sec-title">Ko'nikmalar</div>
    <div class="badges-wrap">
      {%- for s in d.skills -%}<span class="badge">{{ s }}</span>{%- endfor -%}
    </div>
  </div>
  {%- endif -%}
{%- endmacro -%}

{#── MINIMAL ─────────────────────────────────────────────────────────────────#}
{%- if tpl == 'minimal' -%}
<div class="cv-canvas tpl-minimal">
  <div class="header">
    {%- if d.img -%}<img src="{{ d.img }}" class="avatar" alt="avatar">{%- endif -%}
    <div>
      <div class="name">{{ d.name or 'Ism Familiya' }}</div>
      <div class="role">{{ d.role or '' }}</div>
      <div class="contact-wrap">
        {%- if d.phone -%}<span>📞 {{ d.phone }}</span>{%- endif -%}
        {%- if d.email -%}<span>✉️ {{ d.email }}</span>{%- endif -%}
        {%- if d.loc -%}<span>📍 {{ d.loc }}</span>{%- endif -%}
      </div>
    </div>
  </div>
  {%- if d.about -%}
  <div class="section"><div class="sec-title">Haqida</div><div class="text">{{ d.about }}</div></div>
  {%- endif -%}
  {{ expBlock() }}
  {{ eduBlock() }}
  {{ skillsBlock() }}
</div>

{#── SPLIT ──────────────────────────────────────────────────────────────────#}
{%- elif tpl == 'split' -%}
<div class="cv-canvas tpl-split">
  <div class="sidebar">
    {%- if d.img -%}<img src="{{ d.img }}" class="avatar" alt="avatar">{%- endif -%}
    <div class="section">
      <div class="sec-title-side">Aloqa</div>
      {%- if d.phone -%}<div class="contact-item">📞 {{ d.phone }}</div>{%- endif -%}
      {%- if d.email -%}<div class="contact-item">✉️ {{ d.email }}</div>{%- endif -%}
      {%- if d.loc -%}<div class="contact-item">📍 {{ d.loc }}</div>{%- endif -%}
    </div>
    {%- if d.skills -%}
    <div class="section">
      <div class="sec-title-side">Ko'nikmalar</div>
      <div class="badges-wrap">{%- for s in d.skills -%}<span class="badge">{{ s }}</span>{%- endfor -%}</div>
    </div>
    {%- endif -%}
  </div>
  <div class="main">
    <div class="name">{{ d.name or 'Ism Familiya' }}</div>
    <div class="role">{{ d.role or '' }}</div>
    {%- if d.about -%}
    <div class="section"><div class="sec-title-main">Haqida</div><div class="text">{{ d.about }}</div></div>
    {%- endif -%}
    {%- if d.experiences -%}
    <div class="section">
      <div class="sec-title-main">Ish tajribasi</div>
      {%- for e in d.experiences -%}
      <div class="item-row">
        <div class="item-head"><span class="item-title">{{ e.title }}</span><span class="item-date">{{ e.date }}</span></div>
        {%- if e.company -%}<div class="item-sub">{{ e.company }}</div>{%- endif -%}
        {%- if e.desc -%}<div class="item-desc">{{ e.desc | replace('\\n','<br>') | safe }}</div>{%- endif -%}
      </div>
      {%- endfor -%}
    </div>
    {%- endif -%}
    {%- if d.education -%}
    <div class="section">
      <div class="sec-title-main">Ta'lim</div>
      {%- for e in d.education -%}
      <div class="item-row">
        <div class="item-head"><span class="item-title">{{ e.title }}</span><span class="item-date">{{ e.date }}</span></div>
        {%- if e.company -%}<div class="item-sub">{{ e.company }}</div>{%- endif -%}
      </div>
      {%- endfor -%}
    </div>
    {%- endif -%}
  </div>
</div>

{#── MODERN ──────────────────────────────────────────────────────────────────#}
{%- elif tpl == 'modern' -%}
<div class="cv-canvas tpl-modern">
  <div class="header">
    {%- if d.img -%}<img src="{{ d.img }}" class="avatar" alt="avatar">{%- endif -%}
    <div class="header-info">
      <div class="name">{{ d.name or 'Ism Familiya' }}</div>
      <div class="role">{{ d.role or '' }}</div>
      <div class="contact">
        {%- if d.phone or d.email -%}<div>
          {%- if d.phone -%}📞 {{ d.phone }}{%- endif -%}
          {%- if d.phone and d.email %} &nbsp;|&nbsp; {%- endif -%}
          {%- if d.email -%}✉️ {{ d.email }}{%- endif -%}
        </div>{%- endif -%}
        {%- if d.loc -%}<div>📍 {{ d.loc }}</div>{%- endif -%}
      </div>
    </div>
  </div>
  <div class="body">
    <div class="col-main">
      {%- if d.about -%}<div class="section"><div class="sec-title">Haqida</div><div class="text">{{ d.about }}</div></div>{%- endif -%}
      {{ expBlock() }}
    </div>
    <div class="col-side">
      {{ eduBlock() }}
      {{ skillsBlock() }}
    </div>
  </div>
</div>

{#── ATS SAFE ────────────────────────────────────────────────────────────────#}
{%- elif tpl == 'ats' -%}
<div class="cv-canvas tpl-ats">
  <div class="header">
    <div class="name">{{ d.name or 'Ism Familiya' }}</div>
    <div class="role">{{ d.role or '' }}</div>
    <div class="contact-wrap">
      {%- if d.phone -%}<span>📞 {{ d.phone }}</span>{%- endif -%}
      {%- if d.email -%}<span>✉️ {{ d.email }}</span>{%- endif -%}
      {%- if d.loc -%}<span>📍 {{ d.loc }}</span>{%- endif -%}
    </div>
  </div>
  {%- if d.about -%}<div class="section"><div class="sec-title">Haqida</div><div class="text">{{ d.about }}</div></div>{%- endif -%}
  {{ expBlock() }}
  {{ eduBlock() }}
  {%- if d.skills -%}
  <div class="section"><div class="sec-title">Ko'nikmalar</div><div style="font-size:10pt;">{{ d.skills | join(', ') }}</div></div>
  {%- endif -%}
</div>

{#── ELEGANT ─────────────────────────────────────────────────────────────────#}
{%- elif tpl == 'elegant' -%}
<div class="cv-canvas tpl-elegant">
  <div class="header">
    <div class="name">{{ d.name or 'Ism Familiya' }}</div>
    <div class="role">{{ d.role or '' }}</div>
    <div class="contact-wrap">
      {%- if d.phone -%}{{ d.phone }}{%- endif -%}
      {%- if d.email -%} &nbsp;·&nbsp; {{ d.email }}{%- endif -%}
      {%- if d.loc -%} &nbsp;·&nbsp; {{ d.loc }}{%- endif -%}
    </div>
  </div>
  <div class="body-cols">
    <div class="col-main">
      {%- if d.about -%}<div class="section"><div class="sec-title">Haqida</div><div class="text">{{ d.about }}</div></div>{%- endif -%}
      {{ expBlock() }}
    </div>
    <div class="col-side">
      {{ eduBlock() }}
      {{ skillsBlock() }}
    </div>
  </div>
</div>

{#── CORPORATE ───────────────────────────────────────────────────────────────#}
{%- elif tpl == 'corporate' -%}
<div class="cv-canvas tpl-corporate">
  <div class="header">
    <div>
      {%- if d.img -%}<img src="{{ d.img }}" class="avatar" style="width:35mm;height:35mm;border-radius:5px;object-fit:cover;margin-bottom:12px;" alt="avatar">{%- endif -%}
      <div class="name">{{ d.name or 'Ism Familiya' }}</div>
      <div class="role">{{ d.role or '' }}</div>
    </div>
    <div class="contact-wrap">
      {%- if d.phone -%}<div>📞 {{ d.phone }}</div>{%- endif -%}
      {%- if d.email -%}<div>✉️ {{ d.email }}</div>{%- endif -%}
      {%- if d.loc -%}<div>📍 {{ d.loc }}</div>{%- endif -%}
    </div>
  </div>
  <div class="body-cols">
    <div class="col-main">
      {%- if d.about -%}<div class="section"><div class="sec-title">Haqida</div><div class="text">{{ d.about }}</div></div>{%- endif -%}
      {{ expBlock() }}
    </div>
    <div class="col-side">
      {{ eduBlock() }}
      {{ skillsBlock() }}
    </div>
  </div>
</div>

{#── CREATIVE ────────────────────────────────────────────────────────────────#}
{%- elif tpl == 'creative' -%}
<div class="cv-canvas tpl-creative">
  <div class="left">
    {%- if d.img -%}<img src="{{ d.img }}" class="avatar" alt="avatar">{%- endif -%}
    <div class="name">{{ d.name or 'Ism' }}</div>
    <div class="role">{{ d.role or '' }}</div>
    <div class="section">
      <div class="sec-title sec-title-left">Aloqa</div>
      {%- if d.phone -%}<div class="contact-item">📞 {{ d.phone }}</div>{%- endif -%}
      {%- if d.email -%}<div class="contact-item">✉️ {{ d.email }}</div>{%- endif -%}
      {%- if d.loc -%}<div class="contact-item">📍 {{ d.loc }}</div>{%- endif -%}
    </div>
    {%- if d.skills -%}
    <div class="section">
      <div class="sec-title sec-title-left">Ko'nikmalar</div>
      <div class="badges-wrap">{%- for s in d.skills -%}<span class="badge">{{ s }}</span>{%- endfor -%}</div>
    </div>
    {%- endif -%}
    {%- if d.education -%}
    <div class="section">
      <div class="sec-title sec-title-left">Ta'lim</div>
      {%- for e in d.education -%}
      <div class="item-row">
        <div style="font-weight:700;font-size:9.5pt;color:#831843;">{{ e.title }}</div>
        <div style="font-size:8.5pt;opacity:0.7;">{{ e.company }}{%- if e.date %} · {{ e.date }}{%- endif -%}</div>
      </div>
      {%- endfor -%}
    </div>
    {%- endif -%}
  </div>
  <div class="right">
    {%- if d.about -%}<div class="section"><div class="sec-title">Haqida</div><div class="text">{{ d.about }}</div></div>{%- endif -%}
    {{ expBlock() }}
  </div>
</div>

{#── PROFESSIONAL ────────────────────────────────────────────────────────────#}
{%- elif tpl == 'prof' -%}
{%- set parts = (d.name or 'Ism Familiya').split(' ') -%}
<div class="cv-canvas tpl-prof">
  <div class="left-strip"></div>
  <div class="content">
    <div class="header">
      {%- if d.img -%}<img src="{{ d.img }}" class="avatar" style="width:35mm;height:35mm;border-radius:5px;object-fit:cover;" alt="avatar">{%- endif -%}
      <div>
        <div class="name"><strong>{{ parts[0] }}</strong>{% if parts|length > 1 %} {{ parts[1:] | join(' ') }}{% endif %}</div>
        <div class="role">{{ d.role or '' }}</div>
        <div class="contact-wrap">
          {%- if d.phone -%}<span>{{ d.phone }}</span>{%- endif -%}
          {%- if d.email -%}<span>· {{ d.email }}</span>{%- endif -%}
          {%- if d.loc -%}<span>· {{ d.loc }}</span>{%- endif -%}
        </div>
      </div>
    </div>
    {%- if d.about -%}<div class="section"><div class="sec-title">Haqida</div><div class="text">{{ d.about }}</div></div>{%- endif -%}
    <div style="display:flex;gap:30px;">
      <div style="flex:2">{{ expBlock() }}</div>
      <div style="flex:1">{{ eduBlock() }}{{ skillsBlock() }}</div>
    </div>
  </div>
</div>

{#── FALLBACK ────────────────────────────────────────────────────────────────#}
{%- else -%}
<div class="cv-canvas tpl-minimal">
  <div class="header">
    <div>
      <div class="name">{{ d.name or 'Ism Familiya' }}</div>
      <div class="role">{{ d.role or '' }}</div>
    </div>
  </div>
  {%- if d.about -%}<div class="section"><p>{{ d.about }}</p></div>{%- endif -%}
</div>
{%- endif -%}
</body>
</html>
"""

with open("templates/cv_template.html", "w", encoding="utf-8") as f:
    f.write(CV_TEMPLATE)

print("cv_template.html written successfully")

# ──────────────────────────────────────────────────────────────────────────────
#  PART 2  — obyektivka_template.html  (extract CSS from obyektivka.html)
# ──────────────────────────────────────────────────────────────────────────────
with open("webapp/obyektivka.html", "r", encoding="utf-8") as f:
    src_oby = f.read().replace("\r\n", "\n")

m2 = re.search(r"<style>(.*?)</style>", src_oby, re.DOTALL)
css_oby = m2.group(1)
css_oby = re.sub(r"@media print\s*\{.*?\}", "", css_oby, flags=re.DOTALL)
css_oby = css_oby.replace("box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);", "")
css_oby = css_oby.replace("margin-bottom: 30px;", "margin: 0;")
css_oby = re.sub(r"body\s*\{\s*overscroll-behavior-y:\s*none;\s*\}", "", css_oby)
css_oby = re.sub(r"\.scroller.*?\}", "", css_oby, flags=re.DOTALL)
css_oby = re.sub(r"\.cv-canvas-wrapper.*?\}", "", css_oby, flags=re.DOTALL)
css_oby += "\n    @page { size: A4; margin: 0; }\n"

OBY_TEMPLATE = """<!DOCTYPE html>
<html lang="uz">
<head>
  <meta charset="UTF-8">
  <title>Ma'lumotnoma — {{ data.fullname }}</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: #fff;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }
""" + css_oby + """
  </style>
</head>
<body>
{%- set d = data -%}
<div class="tpl-oby">

  <div class="title">M A ' L U M O T N O M A</div>

  <table class="header-table">
    <tr>
      <td class="col-main">
        <div class="name">{{ (d.fullname or '—').upper() }}</div>
      </td>
      <td class="col-img">
        {%- if d.img -%}
        <img src="{{ d.img }}" class="avatar" alt="Fotosurat">
        {%- else -%}
        <div style="width:30mm;height:40mm;margin-left:auto;border:1px solid #aaa;display:flex;align-items:center;justify-content:center;color:#aaa;font-size:9pt;">4x6</div>
        {%- endif -%}
      </td>
    </tr>
  </table>

  <div class="info-grid">
    <div class="info-item"><strong>Tug'ilgan yili, kuni va oyi:</strong>{{ d.birthdate or '—' }}</div>
    <div class="info-item"><strong>Tug'ilgan joyi:</strong>{{ d.birthplace or '—' }}</div>
    <div class="info-item"><strong>Millati:</strong>{{ d.nation or '—' }}</div>
    <div class="info-item"><strong>Partiyaviyligi:</strong>{{ d.party or 'Partiyasiz' }}</div>
    <div class="info-item"><strong>Ma'lumoti:</strong>{{ d.education or '—' }}</div>
    <div class="info-item"><strong>Qaysi oliy maktabni tamomlagan:</strong>{{ d.graduated or '—' }}</div>
    <div class="info-item"><strong>Mutaxassisligi:</strong>{{ d.specialty or '—' }}</div>
    <div class="info-item"><strong>Ilmiy darajasi:</strong>{{ d.degree or "yo'q" }}</div>
    <div class="info-item"><strong>Ilmiy unvoni:</strong>{{ d.scientific_title or "yo'q" }}</div>
    <div class="info-item"><strong>Qaysi chet tillarini biladi:</strong>{{ d.languages or '—' }}</div>
    <div class="info-item"><strong>Harbiy unvoni:</strong>{{ d.military_rank or '—' }}</div>
    <div class="info-item"><strong>Davlat mukofotlari:</strong>{{ d.awards or "yo'q" }}</div>
    <div class="info-item" style="grid-column:1/-1"><strong>Deputatmi yoki boshqa saylanadigan organlar a'zosimi:</strong>{{ d.deputy or "yo'q" }}</div>
  </div>

  <div class="section-title">MEHNAT FAOLIYATI</div>
  {%- if d.work_experience and d.work_experience | length > 0 -%}
  <table class="exp-table">
    <thead><tr><th>Yillar</th><th>Ish joyi va lavozimi</th></tr></thead>
    <tbody>
    {%- for e in d.work_experience -%}
    <tr>
      <td>{{ e.year or e.years or '—' }}</td>
      <td>{{ (e.position or e.desc or '—') | replace('\\n', '<br>') | safe }}</td>
    </tr>
    {%- endfor -%}
    </tbody>
  </table>
  {%- else -%}
  <div style="text-align:center;font-style:italic;padding:10px 0;">Ma'lumot kiritilmagan</div>
  {%- endif -%}

  {%- set fn = (d.fullname or '').split(' ')[0] | upper -%}
  <div class="section-title">{{ fn }}NING YAQIN QARINDOSHLARI HAQIDA MA'LUMOT</div>
  {%- if d.relatives and d.relatives | length > 0 -%}
  <table class="rel-table">
    <thead>
      <tr>
        <th style="width:12%">Qarindoshligi</th>
        <th style="width:20%">F.I.SH.</th>
        <th style="width:18%">Tug'ilgan yili va joyi</th>
        <th style="width:28%">Ish joyi va lavozimi</th>
        <th style="width:22%">Yashash manzili</th>
      </tr>
    </thead>
    <tbody>
    {%- for r in d.relatives -%}
    <tr>
      <td>{{ r.degree or r.role or '—' }}</td>
      <td>{{ r.fullname or r.name or '—' }}</td>
      <td>{{ r.birth_year_place or r.birth or '—' }}</td>
      <td>{{ r.work_place or r.work or '—' }}</td>
      <td>{{ r.address or r.addr or '—' }}</td>
    </tr>
    {%- endfor -%}
    </tbody>
  </table>
  {%- else -%}
  <div style="text-align:center;font-style:italic;padding:10px 0;">Ma'lumot kiritilmagan</div>
  {%- endif -%}

</div>
</body>
</html>
"""

with open("templates/obyektivka_template.html", "w", encoding="utf-8") as f:
    f.write(OBY_TEMPLATE)

print("obyektivka_template.html written successfully")
