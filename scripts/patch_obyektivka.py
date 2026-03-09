"""
Patch webapp/obyektivka.html:
1. Add _isTgWebApp() helper
2. Fix exportPDF() to skip browser download in Telegram Mini App
3. Fix exportWord() to skip browser download in Telegram Mini App
"""

path = "webapp/obyektivka.html"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

# ── 1. Add _isTgWebApp() helper before exportPDF ────────────────────────────
TG_HELPER = (
    "            // ── Detect Telegram Mini App environment ─────────────────────\n"
    "            function _isTgWebApp() {\n"
    "                return !!(window.Telegram?.WebApp?.initData);\n"
    "            }\n\n"
)

EXPORT_PDF_OLD = (
    "            // ── exportPDF() — Server-side, pixel-perfect PDF ──────────\n"
    "            async function exportPDF() {\n"
    "                const btn = document.getElementById('btnPdf');\n"
    "                const originalHtml = btn.innerHTML;\n"
    "                btn.innerHTML = '⏳ Kutib turing...';\n"
    "                btn.disabled = true;\n"
    "\n"
    "                const safeName = (_collectObyData('pdf').fullname || 'Obyektivka').replace(/\\s+/g, '_');\n"
    "                const filename = `DASTYOR_Obyektivka_${safeName}_@DastyorAiBot.pdf`;\n"
    "\n"
    "                try {\n"
    "                    const res = await fetch(DastyorAI.BASE + '/api/export_obyektivka', {\n"
    "                        method: 'POST',\n"
    "                        headers: { 'Content-Type': 'application/json' },\n"
    "                        body: JSON.stringify(_collectObyData('pdf')),\n"
    "                    });\n"
    "\n"
    "                    if (!res.ok) throw new Error('Server xatosi: ' + res.status);\n"
    "\n"
    "                    const blob = await res.blob();\n"
    "                    const url = URL.createObjectURL(blob);\n"
    "                    const a = document.createElement('a');\n"
    "                    a.href = url; a.download = filename;\n"
    "                    document.body.appendChild(a); a.click();\n"
    "                    setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 2000);\n"
    "\n"
    "                    _showTelegramToast(DastyorAI.getTelegramId()\n"
    "                        ? '✅ PDF saqlandi va Telegram ga yuborildi!'\n"
    "                        : '✅ PDF saqlandi!');\n"
    "                } catch (err) {\n"
    "                    console.error('exportPDF server error:', err);\n"
    "                    // Fallback: client-side html2pdf.js\n"
    "                    _exportPDFClientSide(filename, btn, originalHtml);\n"
    "                    return;\n"
    "                }\n"
    "\n"
    "                autoScale();\n"
    "                btn.innerHTML = originalHtml;\n"
    "                btn.disabled = false;\n"
    "            }"
)

EXPORT_PDF_NEW = (
    TG_HELPER +
    "            // ── exportPDF() — Server-side, pixel-perfect PDF ──────────\n"
    "            async function exportPDF() {\n"
    "                const inTelegram = _isTgWebApp();\n"
    "                const btn = document.getElementById('btnPdf');\n"
    "                const originalHtml = btn.innerHTML;\n"
    "                btn.innerHTML = '⏳ Kutib turing...';\n"
    "                btn.disabled = true;\n"
    "\n"
    "                const safeName = (_collectObyData('pdf').fullname || 'Obyektivka').replace(/\\s+/g, '_');\n"
    "                const filename = `DASTYOR_Obyektivka_${safeName}_@DastyorAiBot.pdf`;\n"
    "\n"
    "                try {\n"
    "                    const res = await fetch(DastyorAI.BASE + '/api/export_obyektivka', {\n"
    "                        method: 'POST',\n"
    "                        headers: { 'Content-Type': 'application/json' },\n"
    "                        body: JSON.stringify(_collectObyData('pdf')),\n"
    "                    });\n"
    "\n"
    "                    if (!res.ok) throw new Error('Server xatosi: ' + res.status);\n"
    "\n"
    "                    if (inTelegram) {\n"
    "                        // Inside Telegram Mini App: bot sends the file directly. Skip browser download.\n"
    "                        await res.arrayBuffer();\n"
    "                        _showTelegramToast('✅ PDF Telegram chatga yuborildi!');\n"
    "                    } else {\n"
    "                        const blob = await res.blob();\n"
    "                        const url = URL.createObjectURL(blob);\n"
    "                        const a = document.createElement('a');\n"
    "                        a.href = url; a.download = filename;\n"
    "                        document.body.appendChild(a); a.click();\n"
    "                        setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 2000);\n"
    "                        _showTelegramToast('✅ PDF saqlandi!');\n"
    "                    }\n"
    "                } catch (err) {\n"
    "                    console.error('exportPDF server error:', err);\n"
    "                    if (!inTelegram) {\n"
    "                        _exportPDFClientSide(filename, btn, originalHtml);\n"
    "                        return;\n"
    "                    } else {\n"
    "                        _showTelegramToast('❌ Xatolik yuz berdi. Qayta urinib ko\\'ring.');\n"
    "                    }\n"
    "                }\n"
    "\n"
    "                autoScale();\n"
    "                btn.innerHTML = originalHtml;\n"
    "                btn.disabled = false;\n"
    "            }"
)

EXPORT_WORD_OLD = (
    "            // ── exportWord() — Server-side, pixel-perfect Word ────────\n"
    "            async function exportWord() {\n"
    "                const btnEl = document.querySelector('button[onclick=\"exportWord()\"]');\n"
    "                if (btnEl) { btnEl.disabled = true; btnEl.innerHTML = '⏳ Kuting...'; }\n"
    "\n"
    "                const safeName = (_collectObyData('word').fullname || 'Obyektivka').replace(/\\s+/g, '_');\n"
    "                const filename = `DASTYOR_Obyektivka_${safeName}_@DastyorAiBot.doc`;\n"
    "\n"
    "                try {\n"
    "                    const res = await fetch(DastyorAI.BASE + '/api/export_obyektivka', {\n"
    "                        method: 'POST',\n"
    "                        headers: { 'Content-Type': 'application/json' },\n"
    "                        body: JSON.stringify(_collectObyData('word')),\n"
    "                    });\n"
    "\n"
    "                    if (!res.ok) throw new Error('Server xatosi: ' + res.status);\n"
    "\n"
    "                    const blob = await res.blob();\n"
    "                    const url = URL.createObjectURL(blob);\n"
    "                    const a = document.createElement('a');\n"
    "                    a.href = url; a.download = filename;\n"
    "                    document.body.appendChild(a); a.click();\n"
    "                    setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 2000);\n"
    "\n"
    "                    _showTelegramToast(DastyorAI.getTelegramId()\n"
    "                        ? '✅ Word saqlandi va Telegram ga yuborildi!'\n"
    "                        : '✅ Word saqlandi!');\n"
    "                } catch (err) {\n"
    "                    console.error('exportWord server error:', err);\n"
    "                    _exportWordClientSide(filename);\n"
    "                }\n"
    "\n"
    "                if (btnEl) { btnEl.disabled = false; btnEl.innerHTML = '📄 Word'; }\n"
    "            }"
)

EXPORT_WORD_NEW = (
    "            // ── exportWord() — Server-side, pixel-perfect Word ────────\n"
    "            async function exportWord() {\n"
    "                const inTelegram = _isTgWebApp();\n"
    "                const btnEl = document.querySelector('button[onclick=\"exportWord()\"]');\n"
    "                if (btnEl) { btnEl.disabled = true; btnEl.innerHTML = '⏳ Kuting...'; }\n"
    "\n"
    "                const safeName = (_collectObyData('word').fullname || 'Obyektivka').replace(/\\s+/g, '_');\n"
    "                const filename = `DASTYOR_Obyektivka_${safeName}_@DastyorAiBot.doc`;\n"
    "\n"
    "                try {\n"
    "                    const res = await fetch(DastyorAI.BASE + '/api/export_obyektivka', {\n"
    "                        method: 'POST',\n"
    "                        headers: { 'Content-Type': 'application/json' },\n"
    "                        body: JSON.stringify(_collectObyData('word')),\n"
    "                    });\n"
    "\n"
    "                    if (!res.ok) throw new Error('Server xatosi: ' + res.status);\n"
    "\n"
    "                    if (inTelegram) {\n"
    "                        await res.arrayBuffer();\n"
    "                        _showTelegramToast('✅ Word fayl Telegram chatga yuborildi!');\n"
    "                    } else {\n"
    "                        const blob = await res.blob();\n"
    "                        const url = URL.createObjectURL(blob);\n"
    "                        const a = document.createElement('a');\n"
    "                        a.href = url; a.download = filename;\n"
    "                        document.body.appendChild(a); a.click();\n"
    "                        setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 2000);\n"
    "                        _showTelegramToast('✅ Word saqlandi!');\n"
    "                    }\n"
    "                } catch (err) {\n"
    "                    console.error('exportWord server error:', err);\n"
    "                    if (!inTelegram) _exportWordClientSide(filename);\n"
    "                    else _showTelegramToast('❌ Xatolik yuz berdi. Qayta urinib ko\\'ring.');\n"
    "                }\n"
    "\n"
    "                if (btnEl) { btnEl.disabled = false; btnEl.innerHTML = '📄 Word'; }\n"
    "            }"
)

# Normalise to LF for matching, then replace, then restore original line endings
code_lf = code.replace("\r\n", "\n")

old_pdf = EXPORT_PDF_OLD.replace("\r\n", "\n")
new_pdf = EXPORT_PDF_NEW.replace("\r\n", "\n")
old_word = EXPORT_WORD_OLD.replace("\r\n", "\n")
new_word = EXPORT_WORD_NEW.replace("\r\n", "\n")

if old_pdf in code_lf:
    code_lf = code_lf.replace(old_pdf, new_pdf, 1)
    print("✅ exportPDF patched")
else:
    print("❌ exportPDF OLD not found - check spacing")

if old_word in code_lf:
    code_lf = code_lf.replace(old_word, new_word, 1)
    print("✅ exportWord patched")
else:
    print("❌ exportWord OLD not found - check spacing")

with open(path, "w", encoding="utf-8", newline="\r\n") as f:
    f.write(code_lf)

print("Done.")
