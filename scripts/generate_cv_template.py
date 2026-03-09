import re

def main():
    with open("webapp/cv.html", "r", encoding="utf-8") as f:
        cv_html = f.read()

    # Extract styles
    style_match = re.search(r"<style>(.*?)</style>", cv_html, re.DOTALL)
    if not style_match:
        print("Style not found!")
        return
    
    css = style_match.group(1).strip()
    
    # We want to remove the @media print { ... } section as it hides things we need for pdf export
    css = re.sub(r"@media print\s*\{.*\}", "", css, flags=re.DOTALL)
    
    # We remove box-shadow and margin from .cv-canvas for printing
    css = css.replace("box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);", "")
    css = css.replace("margin-bottom: 30px;", "margin: 0;")
    
    # Add page directive
    css += "\n    @page {\n      size: A4;\n      margin: 0;\n    }\n"
    
    jinja_template = f"""<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CV | DASTYOR AI</title>
    <!-- Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@400;600;700;800&display=swap" rel="stylesheet" />
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Inter', sans-serif;
            background: #fff;
            color: #1e293b;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}
        {css}
    </style>
</head>
<body class="text-neutral-900 flex flex-col antialiased">
    {{% set d = data %}}
    {{% set tpl = d.template | default('minimal') %}}

    <!-- MACROS -->
    {{% macro expHtml() %}}
        {{% if d.experiences %}}
        <div class="section">
            <div class="sec-title">Ish tajribasi</div>
            {{% for e in d.experiences %}}
            <div class="item-row">
                <div class="item-head">
                    <span class="item-title">{{{{ e.title }}}}</span>
                    <span class="item-date">{{{{ e.date }}}}</span>
                </div>
                {{% if e.company %}}<div class="item-sub">{{{{ e.company }}}}</div>{{% endif %}}
                {{% if e.desc %}}<div class="item-desc">{{{{ e.desc | replace('\\n', '<br>') | safe }}}}</div>{{% endif %}}
            </div>
            {{% endfor %}}
        </div>
        {{% endif %}}
    {{% endmacro %}}

    {{% macro eduHtml() %}}
        {{% if d.education %}}
        <div class="section">
            <div class="sec-title">Ta'lim</div>
            {{% for e in d.education %}}
            <div class="item-row">
                <div class="item-head">
                    <span class="item-title">{{{{ e.title }}}}</span>
                    <span class="item-date">{{{{ e.date }}}}</span>
                </div>
                {{% if e.company %}}<div class="item-sub">{{{{ e.company }}}}</div>{{% endif %}}
                {{% if e.desc %}}<div class="item-desc">{{{{ e.desc | replace('\\n', '<br>') | safe }}}}</div>{{% endif %}}
            </div>
            {{% endfor %}}
        </div>
        {{% endif %}}
    {{% endmacro %}}

    {{% macro skillsWrap() %}}
        {{% if d.skills %}}
        <div class="section">
            <div class="sec-title">Ko'nikmalar</div>
            <div class="badges-wrap">{{% for s in d.skills %}}<span class="badge">{{{{ s }}}}</span>{{% endfor %}}</div>
        </div>
        {{% endif %}}
    {{% endmacro %}}

    {{% macro atsSkills() %}}
        {{% if d.skills %}}
        <div class="section">
            <div class="sec-title">Ko'nikmalar</div>
            <div style="font-size:10pt;">{{{{ d.skills | join(', ') }}}}</div>
        </div>
        {{% endif %}}
    {{% endmacro %}}

    {{% macro profHtml() %}}
        {{% set parts = (d.name or 'Ism_Familiya').split(' ') %}}
        {{% set first = parts[0] %}}
        {{% set rest = parts[1:] | join(' ') %}}
        {{% if rest %}}
            <strong>{{{{ first }}}}</strong> {{{{ rest }}}}
        {{% else %}}
            <strong>{{{{ first }}}}</strong>
        {{% endif %}}
    {{% endmacro %}}


    <!-- MINIMAL -->
    {{% if tpl == 'minimal' %}}
    <div class="cv-canvas tpl-minimal">
        <div class="header">
            {{% if d.img %}}<img src="{{{{ d.img }}}}" class="avatar" alt="avatar">{{% endif %}}
            <div>
                <div class="name">{{{{ d.name or 'Ism Familiya' }}}}</div>
                <div class="role">{{{{ d.role or '' }}}}</div>
                <div class="contact-wrap">
                    {{% if d.phone %}}<span>📞 {{{{ d.phone }}}}</span>{{% endif %}}
                    {{% if d.email %}}<span>| &nbsp; 📧 {{{{ d.email }}}}</span>{{% endif %}}
                    {{% if d.loc %}}<span>| &nbsp; 📍 {{{{ d.loc }}}}</span>{{% endif %}}
                </div>
            </div>
        </div>
        {{% if d.about %}}
        <div class="section"><div class="sec-title">Haqida</div><div class="text">{{{{ d.about }}}}</div></div>
        {{% endif %}}
        {{{{ expHtml() }}}}
        {{{{ eduHtml() }}}}
        {{{{ skillsWrap() }}}}
    </div>

    <!-- SPLIT -->
    {{% elif tpl == 'split' %}}
    <div class="cv-canvas tpl-split">
        <div class="sidebar">
            {{% if d.img %}}<img src="{{{{ d.img }}}}" class="avatar">{{% endif %}}
            <div class="section">
                <div class="sec-title-side">Aloqa</div>
                {{% if d.phone %}}<div class="contact-item">📞 {{{{ d.phone }}}}</div>{{% endif %}}
                {{% if d.email %}}<div class="contact-item">📧 {{{{ d.email }}}}</div>{{% endif %}}
                {{% if d.loc %}}<div class="contact-item">📍 {{{{ d.loc }}}}</div>{{% endif %}}
            </div>
            {{% if d.skills %}}
            <div class="section"><div class="sec-title-side">Ko'nikmalar</div>
                <div class="badges-wrap" style="color:#000">{{% for s in d.skills %}}<span class="badge">{{{{ s }}}}</span>{{% endfor %}}</div>
            </div>
            {{% endif %}}
        </div>
        <div class="main">
            <div class="name">{{{{ d.name }}}}</div>
            <div class="role">{{{{ d.role }}}}</div>
            {{% if d.about %}}<div class="section"><div class="sec-title-main">Haqida</div><div class="text">{{{{ d.about }}}}</div></div>{{% endif %}}
            {{{{ expHtml() | replace("sec-title", "sec-title-main") }}}}
            {{{{ eduHtml() | replace("sec-title", "sec-title-main") }}}}
        </div>
    </div>

    <!-- MODERN -->
    {{% elif tpl == 'modern' %}}
    <div class="cv-canvas tpl-modern">
        <div class="header">
            {{% if d.img %}}<img src="{{{{ d.img }}}}" class="avatar">{{% endif %}}
            <div class="header-info">
                <div class="name">{{{{ d.name }}}}</div>
                <div class="role">{{{{ d.role }}}}</div>
                <div class="contact">
                    <div>📞 {{{{ d.phone }}}} &nbsp; | &nbsp; 📧 {{{{ d.email }}}}</div>
                    <div>📍 {{{{ d.loc }}}}</div>
                </div>
            </div>
        </div>
        <div class="body">
            <div class="col-main">
                {{% if d.about %}}<div class="section"><div class="sec-title">Haqida</div><div class="text">{{{{ d.about }}}}</div></div>{{% endif %}}
                {{{{ expHtml() }}}}
            </div>
            <div class="col-side">
                {{{{ eduHtml() }}}}
                {{{{ skillsWrap() }}}}
            </div>
        </div>
    </div>

    <!-- ATS -->
    {{% elif tpl == 'ats' %}}
    <div class="cv-canvas tpl-ats">
        <div class="header">
            <div class="name">{{{{ d.name }}}}</div>
            <div class="role">{{{{ d.role }}}}</div>
            <div class="contact-wrap">
                {{% if d.phone %}}<span>📞 {{{{ d.phone }}}}</span>{{% endif %}}
                {{% if d.email %}}<span>📧 {{{{ d.email }}}}</span>{{% endif %}}
                {{% if d.loc %}}<span>📍 {{{{ d.loc }}}}</span>{{% endif %}}
            </div>
        </div>
        {{% if d.about %}}<div class="section"><div class="sec-title">Haqida</div><div class="text">{{{{ d.about }}}}</div></div>{{% endif %}}
        {{{{ expHtml() }}}}
        {{{{ eduHtml() }}}}
        {{{{ atsSkills() }}}}
    </div>

    <!-- ELEGANT -->
    {{% elif tpl == 'elegant' %}}
    <div class="cv-canvas tpl-elegant">
        <div class="header">
            <div class="name">{{{{ d.name }}}}</div>
            <div class="role">{{{{ d.role }}}}</div>
            <div class="contact-wrap">
                {{% if d.phone %}}<span>{{{{ d.phone }}}}</span> {{% endif %}}
                {{% if d.email %}}<span> | {{{{ d.email }}}}</span> {{% endif %}}
                {{% if d.loc %}}<span> | {{{{ d.loc }}}}</span>{{% endif %}}
            </div>
        </div>
        <div class="body-cols">
            <div class="col-main">
                {{% if d.about %}}<div class="section"><div class="sec-title">Haqida</div><div class="text">{{{{ d.about }}}}</div></div>{{% endif %}}
                {{{{ expHtml() }}}}
            </div>
            <div class="col-side">
                {{{{ eduHtml() }}}}
                {{{{ skillsWrap() }}}}
            </div>
        </div>
    </div>

    <!-- CORPORATE -->
    {{% elif tpl == 'corporate' %}}
    <div class="cv-canvas tpl-corporate">
        <div class="header">
            <div>
               <div class="name">{{{{ d.name }}}}</div>
               <div class="role">{{{{ d.role }}}}</div>
            </div>
            <div class="contact-wrap">
               {{% if d.phone %}}<div>{{{{ d.phone }}}}</div>{{% endif %}}
               {{% if d.email %}}<div>{{{{ d.email }}}}</div>{{% endif %}}
               {{% if d.loc %}}<div>{{{{ d.loc }}}}</div>{{% endif %}}
            </div>
        </div>
        <div class="body-cols">
            <div class="col-main">
                {{% if d.about %}}<div class="section"><div class="sec-title">Haqida</div><div class="text">{{{{ d.about }}}}</div></div>{{% endif %}}
                {{{{ expHtml() }}}}
            </div>
            <div class="col-side">
                {{{{ eduHtml() }}}}
                {{% if d.skills %}}
                <div class="section"><div class="sec-title">Ko'nikmalar</div>
                    <div class="badges-wrap" style="color:#000">{{% for s in d.skills %}}<span class="badge">{{{{ s }}}}</span>{{% endfor %}}</div>
                </div>
                {{% endif %}}
            </div>
        </div>
    </div>

    <!-- CREATIVE -->
    {{% elif tpl == 'creative' %}}
    <div class="cv-canvas tpl-creative">
        <div class="left">
            {{% if d.img %}}<img src="{{{{ d.img }}}}" class="avatar">{{% endif %}}
            <div class="name">{{{{ d.name }}}}</div>
            <div class="role">{{{{ d.role }}}}</div>
            
            <div class="section">
                <div class="sec-title sec-title-left">Aloqa</div>
                {{% if d.phone %}}<div class="contact-item">📞 {{{{ d.phone }}}}</div>{{% endif %}}
                {{% if d.email %}}<div class="contact-item">📧 {{{{ d.email }}}}</div>{{% endif %}}
                {{% if d.loc %}}<div class="contact-item">📍 {{{{ d.loc }}}}</div>{{% endif %}}
            </div>
            
            {{% if d.skills %}}
            <div class="section"><div class="sec-title sec-title-left">Ko'nikmalar</div>
                <div class="badges-wrap" style="color:#000">{{% for s in d.skills %}}<span class="badge">{{{{ s }}}}</span>{{% endfor %}}</div>
            </div>
            {{% endif %}}
        </div>
        <div class="right">
            {{% if d.about %}}<div class="section"><div class="sec-title">Haqida</div><div class="text">{{{{ d.about }}}}</div></div>{{% endif %}}
            {{{{ expHtml() }}}}
            {{{{ eduHtml() }}}}
        </div>
    </div>

    <!-- PROF -->
    {{% elif tpl == 'prof' %}}
    <div class="cv-canvas tpl-prof">
        <div class="left-strip"></div>
        <div class="content">
            <div class="header">
                {{% if d.img %}}<img src="{{{{ d.img }}}}" class="avatar" style="width: 35mm; height: 35mm; border-radius: 5px; object-fit: cover;">{{% endif %}}
                <div>
                    <div class="name">{{{{ profHtml() }}}}</div>
                    <div class="role">{{{{ d.role }}}}</div>
                    <div class="contact-wrap">
                        {{% if d.phone %}}<span>{{{{ d.phone }}}}</span>{{% endif %}}
                        {{% if d.email %}}<span>&bull; {{{{ d.email }}}}</span>{{% endif %}}
                        {{% if d.loc %}}<span>&bull; {{{{ d.loc }}}}</span>{{% endif %}}
                    </div>
                </div>
            </div>
            
            {{% if d.about %}}<div class="section"><div class="sec-title">Haqida</div><div class="text">{{{{ d.about }}}}</div></div>{{% endif %}}
            
            <div style="display:flex; gap: 30px;">
                <div style="flex:2">
                    {{{{ expHtml() }}}}
                </div>
                <div style="flex:1">
                    {{{{ eduHtml() }}}}
                    {{{{ skillsWrap() }}}}
                </div>
            </div>
        </div>
    </div>
    
    {{% else %}}
    <div class="cv-canvas tpl-minimal">
        <div class="header">
            <div>
                <div class="name">{{{{ d.name }}}}</div>
                <div class="role">{{{{ d.role }}}}</div>
            </div>
        </div>
        <div class="body">{{% if d.about %}}<p>{{{{ d.about }}}}</p>{{% endif %}}</div>
    </div>
    {{% endif %}}
</body>
</html>
"""

    with open("templates/cv_template.html", "w", encoding="utf-8") as f:
        f.write(jinja_template)

if __name__ == "__main__":
    main()
