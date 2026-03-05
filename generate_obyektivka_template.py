import re

def main():
    with open("webapp/obyektivka.html", "r", encoding="utf-8") as f:
        html_str = f.read()

    # Extract styles
    style_match = re.search(r"<style>(.*?)</style>", html_str, re.DOTALL)
    if not style_match:
        print("Style not found!")
        return
    
    css = style_match.group(1).strip()
    css = re.sub(r"@media print\s*\{.*\}", "", css, flags=re.DOTALL)
    css = css.replace("box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);", "")
    css = css.replace("margin-bottom: 30px;", "margin: 0;")
    css += "\n    @page {\n      size: A4;\n      margin: 0;\n    }\n"
    
    jinja_template = f"""<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <title>Ma'lumotnoma — {{{{ data.fullname }}}}</title>
    <!-- Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Times+New+Roman:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: #fff;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}
        {css}
    </style>
</head>
<body>
    {{% set d = data %}}
    <div class="tpl-oby">
        <div class="title">M A ' L U M O T N O M A</div>
        <table class="header-table">
            <tr>
                <td class="col-main">
                    <div class="name">{{{{ (d.fullname or "—") | replace(' ', '<br>') | safe }}}}</div>
                </td>
                <td class="col-img">
                    {{% if d.img %}}
                    <img src="{{{{ d.img }}}}" class="avatar">
                    {{% else %}}
                    <div style="width:30mm;height:40mm;margin-left:auto;border:1px solid #aaa;display:flex;align-items:center;justify-content:center;color:#aaa;font-size:10pt;">4x6</div>
                    {{% endif %}}
                </td>
            </tr>
        </table>
        <div class="info-grid">
            <div class="info-item"><strong>Tug'ilgan yili, kuni va oyi:</strong>{{{{ d.birthdate or '—' }}}}</div>
            <div class="info-item"><strong>Tug'ilgan joyi:</strong>{{{{ d.birthplace or '—' }}}}</div>
            
            <div class="info-item"><strong>Millati:</strong>{{{{ d.nation or '—' }}}}</div>
            <div class="info-item"><strong>Partiyaviyligi:</strong>{{{{ d.party or 'Partiyasiz' }}}}</div>
            
            <div class="info-item"><strong>Ma'lumoti:</strong>{{{{ d.education or '—' }}}}</div>
            <div class="info-item"><strong>Qaysi oliy maktabni tamomlagan:</strong>{{{{ d.graduated or '—' }}}}</div>
            
            <div class="info-item"><strong>Mutaxassisligi:</strong>{{{{ d.specialty or '—' }}}}</div>
            <div class="info-item"><strong>Ilmiy darajasi:</strong>{{{{ d.degree or "yo'q" }}}}</div>
            
            <div class="info-item"><strong>Ilmiy unvoni:</strong>{{{{ d.scientific_title or "yo'q" }}}}</div>
            <div class="info-item"><strong>Qaysi chet tillarini biladi:</strong>{{{{ d.languages or '—' }}}}</div>
            
            <div class="info-item"><strong>Davlat mukofotlari:</strong>{{{{ d.awards or "yo'q" }}}}</div>
            <div class="info-item"><strong>Xalq deputatlari respublika, viloyat, shahar va tuman Kengashi deputatimi yoki boshqa saylanadigan organlarning a'zosimi:</strong>{{{{ d.deputy or "yo'q" }}}}</div>
        </div>
        
        <div class="section-title">MEHNAT FAOLIYATI</div>
        {{% if d.work_experience and d.work_experience | length > 0 %}}
        <table class="exp-table">
            {{% for e in d.work_experience %}}
            <tr>
                <td>{{{{ e.year }}}}</td>
                <td>- {{{{ e.position | replace('\\n', '<br>') | safe }}}}</td>
            </tr>
            {{% endfor %}}
        </table>
        {{% else %}}
        <div style="text-align:center; font-style:italic">Ma'lumot kiritilmagan</div>
        {{% endif %}}
        
        {{% set fn = (d.fullname or '').split(' ')[0] | upper %}}
        <div class="section-title">{{{{ fn }}}}NING YAQIN QARINDOSHLARI HAQIDA MA'LUMOT</div>
        {{% if d.relatives and d.relatives | length > 0 %}}
        <table class="rel-table">
            <tr>
                <th style="width:12%">Qarindoshligi</th>
                <th style="width:23%">F.I.SH.</th>
                <th style="width:20%">Tug'ilgan yili va joyi</th>
                <th style="width:25%">Ish joyi va lavozimi</th>
                <th style="width:20%">Yashash manzili</th>
            </tr>
            {{% for r in d.relatives %}}
            <tr>
                <td>{{{{ r.degree }}}}</td>
                <td>{{{{ r.fullname }}}}</td>
                <td>{{{{ r.birth_year_place }}}}</td>
                <td>{{{{ r.work_place }}}}</td>
                <td>{{{{ r.address }}}}</td>
            </tr>
            {{% endfor %}}
        </table>
        {{% else %}}
        <div style="text-align:center; font-style:italic">Ma'lumot kiritilmagan</div>
        {{% endif %}}
    </div>
</body>
</html>
"""

    with open("templates/obyektivka_template.html", "w", encoding="utf-8") as f:
        f.write(jinja_template)

if __name__ == "__main__":
    main()
