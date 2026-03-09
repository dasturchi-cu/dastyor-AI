/**
 * smart-autofill.js — DASTYOR AI Smart Form System v1.0
 * Features: Auto-suggest, auto-capitalize, auto-date, phone format, dropdowns, validation
 * Works for both CV and Obyektivka forms in Telegram WebApp
 */
(function () {
  'use strict';

  // ── DATA ──────────────────────────────────────────────────────────────────
  const DATA = {
    regions: [
      // Viloyat va shaharlar
      "Toshkent shahri", "Toshkent viloyati",
      "Andijon viloyati", "Andijon shahri",
      "Farg'ona viloyati", "Farg'ona shahri",
      "Namangan viloyati", "Namangan shahri",
      "Samarqand viloyati", "Samarqand shahri",
      "Buxoro viloyati", "Buxoro shahri",
      "Qashqadaryo viloyati", "Qarshi shahri",
      "Surxondaryo viloyati", "Termiz shahri",
      "Sirdaryo viloyati", "Guliston shahri",
      "Jizzax viloyati", "Jizzax shahri",
      "Navoiy viloyati", "Navoiy shahri",
      "Xorazm viloyati", "Urganch shahri",
      "Qoraqalpog'iston Respublikasi", "Nukus shahri",
      // Toshkent shahri tumanlar
      "Yunusobod tumani", "Mirzo Ulug'bek tumani", "Chilonzor tumani",
      "Shayxontohur tumani", "Uchtepa tumani", "Olmazar tumani",
      "Sergeli tumani", "Yakkasaroy tumani", "Bektemir tumani",
      "Mirobod tumani", "Yashnobod tumani",
      // Andijon tumanlar
      "Andijon tumani", "Asaka tumani", "Baliqchi tumani", "Bo'z tumani",
      "Buloqboshi tumani", "Jalaquduq tumani", "Xo'jaobod tumani",
      "Izboskan tumani", "Marhamat tumani", "Oltinkol tumani",
      "Paxtaobod tumani", "Qo'rg'ontepa tumani", "Shahrixon tumani", "Ulug'nor tumani",
      // Farg'ona tumanlar
      "Oltiariq tumani", "Bag'dod tumani", "Beshariq tumani", "Buvayda tumani",
      "Dang'ara tumani", "Furqat tumani", "Qo'shtepa tumani", "Quva tumani",
      "Rishton tumani", "So'x tumani", "Toshloq tumani", "Uchko'prik tumani",
      "O'zbekiston tumani", "Yozyovon tumani",
      // Samarqand tumanlar
      "Bulung'ur tumani", "Ishtixon tumani", "Jomboy tumani", "Kattaqo'rg'on tumani",
      "Narpay tumani", "Nurobod tumani", "Oqdaryo tumani", "Pastdarg'om tumani",
      "Payariq tumani", "Qo'shrabot tumani", "Toyloq tumani", "Urgut tumani",
      // Namangan tumanlar
      "Chortoq tumani", "Chust tumani", "Kosonsoy tumani", "Mingbuloq tumani",
      "Namangan tumani", "Norin tumani", "Pop tumani", "To'raqo'rg'on tumani",
      "Uychi tumani", "Yangiqo'rg'on tumani",
    ],

    universities: [
      "O'zbekiston Milliy Universiteti (O'zMU)",
      "Toshkent Davlat Texnika Universiteti (TDTU)",
      "Toshkent Davlat Yuridik Universiteti (TDYU)",
      "Toshkent Davlat Iqtisodiyot Universiteti (TDIU)",
      "O'zbekiston Davlat Jahon Tillari Universiteti (UZJTU)",
      "Toshkent Tibbiyot Akademiyasi (TTA)",
      "Toshkent Axborot Texnologiyalari Universiteti (TATU)",
      "O'zbekiston Davlat Jismoniy Tarbiya va Sport Universiteti",
      "O'zbekiston Davlat Konservatoriyasi",
      "O'zbekiston Milliy Iqtisodiyot Universiteti (IQTISODIYOT)",
      "Samarqand Davlat Universiteti (SamDU)",
      "Samarqand Davlat Tibbiyot Universiteti (SamDTU)",
      "Andijon Davlat Universiteti (ADU)",
      "Andijon Davlat Tibbiyot Instituti (ADTI)",
      "Farg'ona Davlat Universiteti (FarDU)",
      "Namangan Davlat Universiteti (NamDU)",
      "Buxoro Davlat Universiteti (BuxDU)",
      "Qarshi Davlat Universiteti (QarDU)",
      "Nukus Davlat Pedagogika Instituti",
      "Urganch Davlat Universiteti (UrDU)",
      "Navoiy Davlat Pedagogika Instituti",
      "Termiz Davlat Universiteti (TerDU)",
      "Jizzax Davlat Pedagogika Instituti (JizPI)",
      "Guliston Davlat Universiteti (GulDU)",
      "Harbiy Akademiya",
      "Milliy Gvardiya Harbiy Instituti",
      "Ichki Ishlar Vazirligi Akademiyasi",
      "Davlat Soliq Qo'mitasi Akademiyasi",
      "O'rta maxsus kasb-hunar ta'limi",
    ],

    specializations: [
      // Huquq
      "Huquqshunos", "Yurist", "Advokat", "Prokuror", "Hakim",
      "Xalqaro huquq", "Fuqarolik huquqi", "Jinoyat huquqi", "Ma'muriy huquq",
      // Iqtisodiyot
      "Iqtisodchi", "Buxgalter", "Moliyachi", "Auditor", "Bankir",
      "Menejment va marketing", "Biznes boshqaruvi", "Soliq va soliqqa tortish",
      // Texnik
      "Dasturchi", "IT mutaxassis", "Muhandis", "Elektr muhandisi",
      "Qurilish muhandisi", "Mexanik muhandis", "Kimyo muhandisi", "Neft va gaz muhandisi",
      // Tibbiyot
      "Terapevt", "Jarroh", "Pediatr", "Stomatolog", "Farmatsevt",
      "Psixiatr", "Kardiolog", "Nevropatolog", "Radiolog", "Ginekolog",
      // Ta'lim
      "Pedagog", "O'qituvchi", "Tarbiyachi", "Metodist",
      "O'zbek tili va adabiyoti o'qituvchisi", "Matematika o'qituvchisi",
      "Tarix o'qituvchisi", "Ingliz tili o'qituvchisi", "Fizika o'qituvchisi",
      // Davlat xizmati
      "Davlat xizmatchisi", "Hokimiyat xodimi",
      "Soliq inspektori", "Bojxona xodimi", "Politsiya xodimi",
      // Qishloq xo'jaligi
      "Agrotexnik", "Zootexnik", "Veterinar", "Agronomist",
      // Boshqa
      "Jurnalist", "Arxitektor", "Dizayner", "Psixolog", "Sotsiolog", "Diplomat",
    ],

    govOrgs: [
      "O'zbekiston Respublikasi Prezidenti Administratsiyasi",
      "Vazirlar Mahkamasi", "Mudofaa vazirligi", "Ichki Ishlar vazirligi",
      "Adliya vazirligi", "Moliya vazirligi", "Iqtisodiyot va moliya vazirligi",
      "Sog'liqni saqlash vazirligi", "Xalq ta'limi vazirligi",
      "Oliy va o'rta maxsus ta'lim vazirligi", "Qishloq xo'jaligi vazirligi",
      "Energetika vazirligi", "Transport vazirligi",
      "Raqamli texnologiyalar vazirligi", "Tashqi ishlar vazirligi",
      "Savdo vazirligi", "Mehnat vazirligi",
      "Davlat Soliq Qo'mitasi", "Davlat Bojxona Qo'mitasi",
      "Davlat Xavfsizlik Xizmati", "Prokuratura", "Oliy Sud",
      "Konstitutsiyaviy Sud", "Markaziy Bank",
      "Toshkent shahar hokimligi", "Viloyat hokimligi", "Tuman hokimligi",
    ],

    nationalities: [
      "o'zbek", "rus", "qozoq", "qirg'iz", "tojik", "turkman",
      "uyg'ur", "tatar", "koreys", "arman", "ozarbayjon",
      "gruzin", "yahudiy", "nemis", "ukrainalik", "boshqird",
    ],

    parties: [
      "yo'q", "partiyasiz",
      "O'zbekiston Liberal-Demokratik partiyasi (O'zLiDeP)",
      "O'zbekiston Milliy Tiklanish Demokratik partiyasi",
      "O'zbekiston Xalq Demokratik partiyasi (XDP)",
      "O'zbekiston Adolat sotsial-demokratik partiyasi (Adolat)",
      "Ekologik partiya",
    ],

    educationLevels: [
      "oliy", "oliy (bakalavr)", "oliy (magistr)", "oliy (doktorantura)",
      "o'rta maxsus", "o'rta (umumiy)", "boshlang'ich kasb-hunar",
    ],

    degrees: [
      "yo'q", "fan nomzodi", "fan doktori (PhD)", "fan doktori (DSc)",
      "texnika fanlari nomzodi", "iqtisodiyot fanlari nomzodi",
      "huquq fanlari nomzodi", "tibbiyot fanlari nomzodi",
      "pedagogika fanlari nomzodi",
    ],

    titles: [
      "yo'q", "dotsent", "professor", "katta ilmiy xodim", "akademik",
      "xalq o'qituvchisi", "xizmat ko'rsatgan muhandis",
      "xizmat ko'rsatgan shifokor", "xizmat ko'rsatgan iqtisodchi",
      "xizmat ko'rsatgan fan arbobi",
    ],

    languages: [
      "o'zbek tili", "rus tili", "ingliz tili", "nemis tili",
      "fransuz tili", "arab tili", "xitoy tili", "yapon tili",
      "turk tili", "fors tili", "ispan tili",
    ],

    relRoles: [
      "Otasi", "Onasi", "Akasi", "Ukasi", "Opasi", "Singlisi",
      "Turmush o'rtog'i", "O'g'li", "Qizi",
    ],
  };

  // ── CSS ───────────────────────────────────────────────────────────────────
  const CSS = `
    .sf-wrap { position: relative; }

    /* ─ Autocomplete dropdown ─ */
    .sf-suggest {
      position: absolute; top: calc(100% + 5px); left: 0; right: 0;
      background: #ffffff;
      border: 1px solid rgba(0,0,0,0.09);
      border-radius: 16px;
      max-height: 230px; overflow-y: auto;
      z-index: 9999;
      box-shadow: 0 10px 36px rgba(0,0,0,0.14);
      display: none;
    }
    .dark .sf-suggest {
      background: #2c2c2e;
      border-color: rgba(255,255,255,0.09);
      box-shadow: 0 10px 40px rgba(0,0,0,0.5);
    }
    .sf-suggest.sf-open { display: block; }
    .sf-item {
      padding: 12px 16px; cursor: pointer; font-size: 14px;
      color: #1c1c1e; border-bottom: 1px solid rgba(0,0,0,0.05);
      transition: background 0.12s;
    }
    .dark .sf-item { color: #f2f2f7; border-bottom-color: rgba(255,255,255,0.05); }
    .sf-item:last-child { border-bottom: none; }
    .sf-item:hover, .sf-item.sf-hovered { background: rgba(10,132,255,0.1); }
    .sf-item b { color: #0A84FF; font-style: normal; }

    /* ─ Validation ─ */
    .sf-err { font-size: 11px; color: #FF453A; margin-top: 4px; margin-left: 6px; display: none; }
    .sf-err.sf-show { display: block; }
    .sf-valid  { border-color: rgba(48,209,88,0.5) !important; }
    .sf-invalid { border-color: rgba(255,69,58,0.5) !important; }

    /* ─ Dropdown trigger button ─ */
    .sf-dropdown-btn {
      width: 100%; display: flex; align-items: center; justify-content: space-between;
      border: 1px solid transparent; cursor: pointer; outline: none;
      transition: border-color 0.2s; text-align: left;
    }
    .sf-dropdown-btn:hover, .sf-dropdown-btn:focus {
      border-color: rgba(10,132,255,0.5) !important;
    }
    .sf-arrow { font-size: 9px; opacity: 0.35; margin-left: 8px; flex-shrink: 0; }
    .sf-val { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .sf-val-empty { opacity: 0.38; }

    /* Multi-select chips */
    .sf-chips { display: flex; flex-wrap: wrap; gap: 5px; flex: 1; min-width: 0; }
    .sf-chip {
      background: rgba(10,132,255,0.15); color: #0A84FF;
      border-radius: 20px; padding: 2px 9px;
      font-size: 12px; font-weight: 600; white-space: nowrap;
    }

    /* ─ Bottom sheet overlay ─ */
    .sf-overlay {
      position: fixed; inset: 0; background: rgba(0,0,0,0.48);
      z-index: 99998; display: none; align-items: flex-end;
      backdrop-filter: blur(3px);
    }
    .sf-overlay.sf-open { display: flex; }
    .sf-sheet {
      background: #f2f2f7; border-radius: 20px 20px 0 0;
      width: 100%; max-height: 72vh; overflow-y: auto;
      padding-bottom: max(env(safe-area-inset-bottom, 0px), 16px);
    }
    .dark .sf-sheet { background: #1c1c1e; }
    .sf-sheet-handle {
      width: 38px; height: 4px; background: rgba(0,0,0,0.18);
      border-radius: 2px; margin: 14px auto 0;
    }
    .dark .sf-sheet-handle { background: rgba(255,255,255,0.18); }
    .sf-sheet-title {
      font-weight: 700; font-size: 12px; text-align: center;
      color: rgba(0,0,0,0.35); letter-spacing: 0.5px;
      text-transform: uppercase; padding: 12px 20px;
      border-bottom: 1px solid rgba(0,0,0,0.07); margin-bottom: 4px;
    }
    .dark .sf-sheet-title { color: rgba(255,255,255,0.32); border-bottom-color: rgba(255,255,255,0.07); }
    .sf-sheet-item {
      padding: 15px 20px; font-size: 16px; color: #1c1c1e; cursor: pointer;
      border-bottom: 1px solid rgba(0,0,0,0.05);
      display: flex; align-items: center; justify-content: space-between;
    }
    .dark .sf-sheet-item { color: #f2f2f7; border-bottom-color: rgba(255,255,255,0.06); }
    .sf-sheet-item:hover { background: rgba(10,132,255,0.08); }
    .sf-sheet-item.sf-checked { color: #0A84FF; font-weight: 600; }
    .sf-check { font-size: 17px; opacity: 0; }
    .sf-sheet-item.sf-checked .sf-check { opacity: 1; }
    .sf-done-btn {
      display: block; width: calc(100% - 32px); margin: 14px 16px 0;
      padding: 15px; background: #0A84FF; color: #fff; border: none;
      border-radius: 14px; font-weight: 700; font-size: 15px; cursor: pointer;
    }
    .sf-done-btn:active { background: #0070d8; }

    /* ─ Date hint ─ */
    .sf-date-hint {
      font-size: 10px; color: rgba(0,0,0,0.3); margin-top: 4px; margin-left: 6px;
    }
    .dark .sf-date-hint { color: rgba(255,255,255,0.28); }
  `;

  // ── UTILS ─────────────────────────────────────────────────────────────────
  function esc(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // Capitalizes first letter of each word (works with Uzbek Latin)
  function titleCase(s) {
    if (!s) return s;
    return s.replace(/(^|[\s\-])([^\s\-])/g, (m, sep, c) => sep + c.toUpperCase());
  }

  // Format raw digits into DD.MM.YYYY
  function fmtDate(digits) {
    const d = digits.slice(0, 8);
    if (d.length <= 2) return d;
    if (d.length <= 4) return d.slice(0,2) + '.' + d.slice(2);
    return d.slice(0,2) + '.' + d.slice(2,4) + '.' + d.slice(4);
  }

  // Format phone number: 998XXXXXXXXX → +998 XX XXX-XX-XX
  function fmtPhone(raw) {
    let d = raw.replace(/\D/g, '');
    if (!d) return raw;
    if (d.startsWith('0')) d = '998' + d.slice(1);
    else if (!d.startsWith('998') && d.length <= 9) d = '998' + d;
    d = d.slice(0, 12);
    const parts = [
      '+' + d.slice(0,3),
      d.slice(3,5),
      d.slice(5,8),
      d.slice(8,10),
      d.slice(10,12),
    ].filter(p => p.replace('+','').length);
    if (d.length <= 3) return parts[0];
    if (d.length <= 5) return parts.slice(0,2).join(' ');
    if (d.length <= 8) return parts.slice(0,3).join(' ');
    if (d.length <= 10) return parts.slice(0,3).join(' ') + '-' + parts[3];
    return parts.slice(0,3).join(' ') + '-' + parts[3] + '-' + parts[4];
  }

  // Search items case-insensitively, prefix-first
  function search(query, list, max) {
    if (!query || query.length < 1) return [];
    const q = query.toLowerCase().replace(/[ʻʼ'`]/g, "'");
    const normalize = s => s.toLowerCase().replace(/[ʻʼ'`]/g, "'");
    const starts = [], contains = [];
    for (const item of list) {
      const n = normalize(item);
      if (n.startsWith(q)) starts.push(item);
      else if (n.includes(q)) contains.push(item);
    }
    return [...starts, ...contains].slice(0, max || 8);
  }

  // Highlight matched text
  function hlMatch(text, q) {
    const norm = s => s.toLowerCase().replace(/[ʻʼ'`]/g, "'");
    const idx = norm(text).indexOf(norm(q));
    if (idx < 0) return esc(text);
    return esc(text.slice(0,idx)) + '<b>' + esc(text.slice(idx, idx+q.length)) + '</b>' + esc(text.slice(idx+q.length));
  }

  // Fire native input event (triggers oninput handlers)
  function fireInput(el) {
    el.dispatchEvent(new Event('input', { bubbles: true }));
  }

  // Guard: skip if already initialized
  function guard(el, key) {
    if (!el || el['_sf_' + key]) return false;
    el['_sf_' + key] = true;
    return true;
  }

  // ── INJECT CSS ────────────────────────────────────────────────────────────
  function injectCSS() {
    if (document.getElementById('smart-autofill-css')) return;
    const s = document.createElement('style');
    s.id = 'smart-autofill-css';
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  // ── AUTO-CAPITALIZE ───────────────────────────────────────────────────────
  function initCapitalize(input) {
    if (!guard(input, 'cap')) return;
    input.addEventListener('input', () => {
      const pos = input.selectionStart;
      const cap = titleCase(input.value);
      if (cap !== input.value) {
        input.value = cap;
        try { input.setSelectionRange(pos, pos); } catch (_) {}
      }
    });
  }

  // ── DATE INPUT ────────────────────────────────────────────────────────────
  function initDate(input) {
    if (!guard(input, 'date')) return;
    input.setAttribute('inputmode', 'numeric');
    input.placeholder = input.placeholder || 'KK.OO.YYYY';

    // Add hint
    const hint = document.createElement('div');
    hint.className = 'sf-date-hint';
    hint.textContent = 'Raqamlarni kiriting: 27021990 → 27.02.1990';
    input.parentNode.insertBefore(hint, input.nextSibling);

    input.addEventListener('input', () => {
      const raw = input.value;
      // Only auto-format when user types pure digits (no dots yet)
      if (/^\d{5,}$/.test(raw)) {
        input.value = fmtDate(raw);
        try { input.setSelectionRange(input.value.length, input.value.length); } catch (_) {}
        fireInput(input);
      }
    });

    input.addEventListener('blur', () => {
      const raw = input.value.trim();
      if (!raw) return;
      const digits = raw.replace(/\D/g, '');
      if (digits.length >= 6 && !/^\d{2}\.\d{2}\.\d{4}$/.test(raw)) {
        input.value = fmtDate(digits);
        fireInput(input);
      }
    });
  }

  // ── PHONE INPUT ───────────────────────────────────────────────────────────
  function initPhone(input) {
    if (!guard(input, 'phone')) return;
    input.setAttribute('inputmode', 'tel');
    input.placeholder = input.placeholder || '+998 90 123-45-67';

    // Block non-numeric keys (allow digits, +, backspace, delete, arrows, tab)
    input.addEventListener('keydown', e => {
      if (e.ctrlKey || e.metaKey || e.altKey) return; // allow ctrl+C/V etc.
      const allowed = ['Backspace', 'Delete', 'Tab', 'Enter', 'Escape',
        'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'];
      if (allowed.includes(e.key)) return;
      if (e.key === '+') return;
      if (!/^\d$/.test(e.key)) e.preventDefault();
    });

    // Strip any non-digit chars that arrive via paste or autofill, then format
    input.addEventListener('input', () => {
      const raw = input.value;
      // Remove anything that's not a digit or +
      const cleaned = raw.replace(/[^\d+]/g, '');
      const digits = cleaned.replace(/\D/g, '');
      if (digits.length >= 4) {
        const formatted = fmtPhone(cleaned);
        if (formatted !== raw) {
          input.value = formatted;
          try { input.setSelectionRange(input.value.length, input.value.length); } catch (_) {}
          fireInput(input);
        }
      } else if (cleaned !== raw) {
        input.value = cleaned;
        try { input.setSelectionRange(input.value.length, input.value.length); } catch (_) {}
      }
    });

    // Handle paste — strip letters before processing
    input.addEventListener('paste', e => {
      e.preventDefault();
      const pasted = (e.clipboardData || window.clipboardData).getData('text');
      const digits = pasted.replace(/\D/g, '');
      input.value = digits;
      fireInput(input);
    });
  }

  // ── AUTOCOMPLETE ──────────────────────────────────────────────────────────
  function initAutocomplete(input, dataList, opts) {
    if (!guard(input, 'ac')) return;
    opts = opts || {};

    // Wrap
    const wrap = document.createElement('div');
    wrap.className = 'sf-wrap';
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);

    // Dropdown
    const drop = document.createElement('div');
    drop.className = 'sf-suggest';
    wrap.appendChild(drop);

    let focusIdx = -1;

    function renderItems(query) {
      const matches = search(query, dataList, opts.max || 8);
      if (!matches.length) { closeDrop(); return; }
      drop.innerHTML = matches.map(m =>
        `<div class="sf-item" data-val="${esc(m)}">${hlMatch(m, query)}</div>`
      ).join('');
      drop.classList.add('sf-open');
      focusIdx = -1;
      drop.querySelectorAll('.sf-item').forEach(el => {
        el.addEventListener('mousedown', e => {
          e.preventDefault();
          selectVal(el.dataset.val);
        });
      });
    }

    function selectVal(val) {
      input.value = opts.capitalize ? titleCase(val) : val;
      closeDrop();
      fireInput(input);
    }

    function closeDrop() {
      drop.classList.remove('sf-open');
      focusIdx = -1;
    }

    input.addEventListener('input', () => {
      if (opts.capitalize) {
        const pos = input.selectionStart;
        const cap = titleCase(input.value);
        if (cap !== input.value) {
          input.value = cap;
          try { input.setSelectionRange(pos, pos); } catch (_) {}
        }
      }
      if (input.value.length >= 1) renderItems(input.value);
      else closeDrop();
    });

    input.addEventListener('keydown', e => {
      const items = drop.querySelectorAll('.sf-item');
      if (!items.length) return;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        focusIdx = Math.min(focusIdx + 1, items.length - 1);
        items.forEach((el, i) => el.classList.toggle('sf-hovered', i === focusIdx));
        if (items[focusIdx]) items[focusIdx].scrollIntoView({ block: 'nearest' });
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        focusIdx = Math.max(focusIdx - 1, 0);
        items.forEach((el, i) => el.classList.toggle('sf-hovered', i === focusIdx));
      } else if (e.key === 'Enter' && focusIdx >= 0) {
        e.preventDefault();
        if (items[focusIdx]) selectVal(items[focusIdx].dataset.val);
      } else if (e.key === 'Escape') {
        closeDrop();
      }
    });

    input.addEventListener('focus', () => {
      if (input.value.length >= 1) renderItems(input.value);
    });

    input.addEventListener('blur', () => {
      setTimeout(closeDrop, 200);
    });
  }

  // ── DROPDOWN PICKER (bottom sheet) ───────────────────────────────────────
  function initDropdown(input, options, opts) {
    if (!guard(input, 'dd')) return;
    opts = opts || {};
    const multi = !!opts.multi;
    let selected = input.value
      ? (multi ? input.value.split(', ').map(s => s.trim()).filter(Boolean) : [input.value.trim()])
      : [];

    // Preserve original input classes for button
    const origClass = input.className;
    input.style.display = 'none';

    // Trigger button
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = origClass + ' sf-dropdown-btn';
    input.parentNode.insertBefore(btn, input.nextSibling);

    function updateBtn() {
      if (multi && selected.length) {
        btn.innerHTML = `<span class="sf-chips">${selected.map(s => `<span class="sf-chip">${esc(s)}</span>`).join('')}</span><span class="sf-arrow">▼</span>`;
      } else if (!multi && selected[0]) {
        btn.innerHTML = `<span class="sf-val">${esc(selected[0])}</span><span class="sf-arrow">▼</span>`;
      } else {
        btn.innerHTML = `<span class="sf-val sf-val-empty">${esc(opts.placeholder || 'Tanlang...')}</span><span class="sf-arrow">▼</span>`;
      }
    }
    updateBtn();

    // Bottom sheet
    const overlay = document.createElement('div');
    overlay.className = 'sf-overlay';
    const sheet = document.createElement('div');
    sheet.className = 'sf-sheet';

    sheet.innerHTML = `<div class="sf-sheet-handle"></div><div class="sf-sheet-title">${esc(opts.label || 'Tanlang')}</div>`;
    const optsCont = document.createElement('div');
    sheet.appendChild(optsCont);
    overlay.appendChild(sheet);
    document.body.appendChild(overlay);

    function renderOpts() {
      optsCont.innerHTML = options.map(o =>
        `<div class="sf-sheet-item${selected.includes(o) ? ' sf-checked' : ''}" data-val="${esc(o)}">${esc(o)}<span class="sf-check">✓</span></div>`
      ).join('');

      optsCont.querySelectorAll('.sf-sheet-item').forEach(el => {
        el.addEventListener('click', () => {
          const val = el.dataset.val;
          if (multi) {
            if (selected.includes(val)) {
              selected = selected.filter(s => s !== val);
              el.classList.remove('sf-checked');
            } else {
              selected.push(val);
              el.classList.add('sf-checked');
            }
          } else {
            selected = [val];
            input.value = val;
            updateBtn();
            fireInput(input);
            close();
          }
        });
      });

      if (multi) {
        const done = document.createElement('button');
        done.className = 'sf-done-btn';
        done.textContent = '✓  Tayyor';
        done.addEventListener('click', () => {
          const val = selected.join(', ');
          input.value = val;
          updateBtn();
          fireInput(input);
          close();
        });
        optsCont.appendChild(done);
      }
    }

    function open() {
      renderOpts();
      overlay.classList.add('sf-open');
      document.body.style.overflow = 'hidden';
    }

    function close() {
      overlay.classList.remove('sf-open');
      document.body.style.overflow = '';
    }

    btn.addEventListener('click', open);
    overlay.addEventListener('click', e => { if (e.target === overlay) close(); });
  }

  // ── MAIN INIT ─────────────────────────────────────────────────────────────
  function init() {
    injectCSS();

    const locs = [...DATA.regions, ...DATA.govOrgs];
    const edus = [...DATA.universities];

    // ─ OBYEKTIVKA fields ─────────────────────────────────────────
    initCapitalize(document.getElementById('f_name'));
    initDate(document.getElementById('f_birth'));
    initAutocomplete(document.getElementById('f_place'), locs, { capitalize: true });
    initDropdown(document.getElementById('f_nation'), DATA.nationalities, { label: 'Millati', placeholder: "o'zbek" });
    initDropdown(document.getElementById('f_party'), DATA.parties, { label: 'Partiyaviyligi', placeholder: "yo'q" });
    initDropdown(document.getElementById('f_edu'), DATA.educationLevels, { label: "Ma'lumoti", placeholder: 'oliy' });
    initAutocomplete(document.getElementById('f_grad'), edus, { capitalize: true });
    initAutocomplete(document.getElementById('f_spec'), DATA.specializations, { capitalize: true });
    initDropdown(document.getElementById('f_degree'), DATA.degrees, { label: 'Ilmiy darajasi', placeholder: "yo'q" });
    initDropdown(document.getElementById('f_title'), DATA.titles, { label: 'Ilmiy unvoni', placeholder: "yo'q" });
    initDropdown(document.getElementById('f_langs'), DATA.languages, { label: 'Tillar (bir nechta tanlash mumkin)', placeholder: "o'zbek tili", multi: true });
    initPhone(document.getElementById('f_phone'));
    initAutocomplete(document.getElementById('f_addr'), locs, { capitalize: true });

    // ─ CV fields ─────────────────────────────────────────────────
    // f_name, f_phone — already handled above (guard prevents double-init)
    initAutocomplete(document.getElementById('f_role'), DATA.specializations, { capitalize: true });
    initAutocomplete(document.getElementById('f_loc'), locs, { capitalize: true });

    // ─ CV dynamic fields (exp/edu lists) ────────────────────────
    initDynamic();
  }

  // ── DYNAMIC CV FIELDS (called after renderExp/renderEdu) ──────────────────
  function initDynamic() {
    // Experience: Lavozim (job title)
    document.querySelectorAll('#expList [placeholder="Lavozim"]').forEach(el => {
      initAutocomplete(el, DATA.specializations, { capitalize: true });
    });

    // Experience: Kompaniya (company) — gov orgs + free text
    document.querySelectorAll('#expList [placeholder="Kompaniya"]').forEach(el => {
      initAutocomplete(el, DATA.govOrgs, { capitalize: true });
    });

    // Education: Oliygoh (university)
    document.querySelectorAll('#eduList [placeholder="Oliygoh"]').forEach(el => {
      initAutocomplete(el, DATA.universities, { capitalize: true });
    });

    // Education: Daraja yoki Kurs (degree/course)
    document.querySelectorAll('#eduList [placeholder="Daraja yoki Kurs"]').forEach(el => {
      initDropdown(el, [
        'Bakalavr', 'Magistr', 'PhD (Doktorantura)', 'DSc (Fan doktori)',
        "O'rta maxsus (kollej)", 'Kurs / Sertifikat', 'Aspirantura',
        "Boshlang'ich kasb-hunar",
      ], { label: "Ma'lumot darajasi", placeholder: 'Bakalavr' });
    });
  }

  // Run after DOM
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    setTimeout(init, 0);
  }

  // Expose globally for external use if needed
  window.SmartAutoFill = { DATA, initCapitalize, initDate, initPhone, initAutocomplete, initDropdown, initDynamic };

})();
