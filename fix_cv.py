import re

with open('webapp/cv.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix TPL-SPLIT
text = text.replace(
    '.tpl-split {\n      display: flex;',
    '.tpl-split {\n      display: table;\n      width: 100%;'
)
text = text.replace(
    '.tpl-split .sidebar {\n      width: 32%;',
    '.tpl-split .sidebar {\n      display: table-cell;\n      vertical-align: top;\n      width: 32%;'
)
text = text.replace(
    '.tpl-split .main {\n      width: 68%;',
    '.tpl-split .main {\n      display: table-cell;\n      vertical-align: top;\n      width: 68%;'
)

# Fix TPL-MODERN
text = text.replace(
    '.tpl-modern .body {\n      display: flex;',
    '.tpl-modern .body {\n      display: table;\n      width: 100%;\n      box-sizing: border-box;'
)
text = text.replace(
    '.tpl-modern .col-main {\n      flex: 6;',
    '.tpl-modern .col-main {\n      display: table-cell;\n      vertical-align: top;\n      width: 60%;'
)
text = text.replace(
    '.tpl-modern .col-side {\n      flex: 4;',
    '.tpl-modern .col-side {\n      display: table-cell;\n      vertical-align: top;\n      width: 40%;'
)

# Fix TPL-ELEGANT
text = text.replace(
    '.tpl-elegant .body-cols {\n      display: flex;',
    '.tpl-elegant .body-cols {\n      display: table;\n      width: 100%;'
)
text = text.replace(
    '.tpl-elegant .col-main {\n      flex: 2;',
    '.tpl-elegant .col-main {\n      display: table-cell;\n      vertical-align: top;\n      width: 66%;'
)
text = text.replace(
    '.tpl-elegant .col-side {\n      flex: 1;',
    '.tpl-elegant .col-side {\n      display: table-cell;\n      vertical-align: top;\n      width: 33%;'
)

# Fix TPL-CORPORATE
text = text.replace(
    '.tpl-corporate .body-cols {\n      display: flex;',
    '.tpl-corporate .body-cols {\n      display: table;\n      width: 100%;'
)
text = text.replace(
    '.tpl-corporate .col-main {\n      flex: 7;',
    '.tpl-corporate .col-main {\n      display: table-cell;\n      vertical-align: top;\n      width: 70%;'
)
text = text.replace(
    '.tpl-corporate .col-side {\n      flex: 3;',
    '.tpl-corporate .col-side {\n      display: table-cell;\n      vertical-align: top;\n      width: 30%;'
)

# Fix TPL-CREATIVE
text = text.replace(
    '.tpl-creative {\n      padding: 0;\n      display: flex;',
    '.tpl-creative {\n      padding: 0;\n      display: table;\n      width: 100%;'
)
text = text.replace(
    '.tpl-creative .left {\n      width: 35%;',
    '.tpl-creative .left {\n      display: table-cell;\n      vertical-align: top;\n      width: 35%;'
)
text = text.replace(
    '.tpl-creative .right {\n      width: 65%;',
    '.tpl-creative .right {\n      display: table-cell;\n      vertical-align: top;\n      width: 65%;'
)

# Fix JS export functions in cv.html
js_replace = """
    // ── Telegram POST helper ──────────────────────────────────────────
    function uploadToTelegram(blob, filename, isPdf=false) {
      const tgId = DastyorAI.getTelegramId();
      if (!tgId) return;
      const formData = new FormData();
      formData.append('file', blob, filename);
      formData.append('telegram_id', tgId);
      if (DastyorAI.getToken()) formData.append('token', DastyorAI.getToken());
      fetch(DastyorAI.BASE + '/api/upload_to_telegram', {
          method: 'POST',
          body: formData
      }).catch(err => console.error("Tg send failed", err));
    }

    function exportPDF() {
      const el = document.getElementById('cv-box');
      const wrap = document.getElementById('previewScaleWrapper');
      wrap.style.transform = 'none';

      const filename = 'DASTYOR_CV_' + new Date().getTime() + '.pdf';
      const opt = {
        margin: 0,
        filename: filename,
        image: { type: 'jpeg', quality: 1.0 },
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
      };

      const btn = document.getElementById('btnPdf');
      const originalHtml = btn.innerHTML;
      btn.innerHTML = I18n.t('status_processing') || "⏳...";
      btn.disabled = true;

      html2pdf().set(opt).from(el).outputPdf('blob').then(blob => {
        // Automatically save to local
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 2000);

        // Upload to Telegram
        uploadToTelegram(blob, filename, true);
        
        autoScale();
        btn.innerHTML = originalHtml;
        btn.disabled = false;
        
        if (DastyorAI.getTelegramId()) {
             _showTelegramToast('✅ PDF tayyor! Telegram ga yuborildi.');
        } else if (tg && tg.showAlert) tg.showAlert(I18n.t('pdf_saved'));
      }).catch(err => {
         btn.innerHTML = originalHtml;
         btn.disabled = false;
         alert("PDF Error: " + err);
      });
    }

    async function exportWord() {
      const btn = document.querySelector('button[onclick="exportWord()"]');
      if (btn) { btn.disabled = true; btn.innerHTML = I18n.t('status_processing') || "⏳..."; }

      const rawHtml = document.getElementById('cv-box').outerHTML;
      const safeName = (document.getElementById('f_name')?.value || 'CV').replace(/\s+/g, '_');
      const docFilename = `DASTYOR_CV_${safeName}.doc`;

      const styles = document.querySelector('style').innerHTML;
      // Inject standard DOC payload
      const docHTML = `
      <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
      <head>
          <meta charset='utf-8'>
          <title>${docFilename}</title>
          <xml>
              <w:WordDocument>
                  <w:View>Print</w:View>
                  <w:Zoom>100</w:Zoom>
                  <w:DoNotOptimizeForBrowser/>
              </w:WordDocument>
          </xml>
          <style>
              @page WordSection1 { size: 210mm 297mm; margin: 15mm; }
              div.WordSection1 { page: WordSection1; }
              ${styles}
          </style>
      </head>
      <body>
          <div class="WordSection1">
              ${rawHtml}
          </div>
      </body>
      </html>`;

      const blob = new Blob(['\\ufeff', docHTML], { type: 'application/msword' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = docFilename;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 2000);

      uploadToTelegram(blob, docFilename, false);

      if (DastyorAI.getTelegramId()) {
         _showTelegramToast('✅ Word fayl bevosita yuklab olindi va Telegram ga yuborildi!');
      } else {
         _showTelegramToast('✅ Word fayl yuklab olindi!');
      }

      if (btn) { btn.disabled = false; btn.innerHTML = '📄 Word'; }
    }
"""

text = re.sub(r'function exportPDF\(\) \{[\s\S]*?\} catch \(err\) \{\n        console\.error\(\'exportWord error:\', err\);\n        alert\(\'Word yaratishda xato: \' \+ err\.message\);\n      \}\n    \}', js_replace, text, flags=re.MULTILINE)

with open('webapp/cv.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('Updated cv.html')
