import ast

with open('api_webhook.py', encoding='utf-8') as f:
    text = f.read()
ast.parse(text)
print('api_webhook.py: OK')

with open('webapp/cv.html', encoding='utf-8') as f:
    cv_text = f.read()
print('cv.html: size =', len(cv_text), 'bytes')

with open('webapp/obyektivka.html', encoding='utf-8') as f:
    obv_text = f.read()
print('obyektivka.html: size =', len(obv_text), 'bytes')

checks = [
    ('cv.html', cv_text, 'uploadToTelegram'),
    ('cv.html', cv_text, 'outputPdf'),
    ('cv.html', cv_text, 'upload_to_telegram'),
    ('cv.html', cv_text, 'WordSection1'),
    ('cv.html', cv_text, '_showTelegramToast'),
    ('obyektivka.html', obv_text, 'uploadToTelegram'),
    ('obyektivka.html', obv_text, 'outputPdf'),
    ('obyektivka.html', obv_text, 'upload_to_telegram'),
    ('obyektivka.html', obv_text, '_showTelegramToast'),
    ('obyektivka.html', obv_text, 'WordSection1'),
    ('api_webhook.py', text, '/api/upload_to_telegram'),
]

all_ok = True
for fname, content, key in checks:
    found = key in content
    status = 'OK' if found else 'MISSING'
    print(f'  [{status}] {fname}: {key}')
    if not found:
        all_ok = False

print('All checks passed!' if all_ok else 'SOME CHECKS FAILED!')
