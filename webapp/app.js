/**
 * DASTYOR AI — Global WebApp SDK
 * - Auth/session API helpers
 * - Global theme (light/dark)
 * - Global i18n (uz/ru/en from /locales/*.json)
 */
const DastyorAI = (() => {
    'use strict';

    /** Production fallback — Railway (file:// yoki origin yo'q bo'lsa). */
    const PROD_API_FALLBACK = 'https://dastyor-ai-production.up.railway.app';

    /**
     * API bazasi: avvalo ?api=, keyin meta[name=dastyor-api-base], keyin joriy origin.
     */
    function resolveApiBase() {
        try {
            const qs = new URLSearchParams(location.search || '');
            const apiQ = qs.get('api');
            if (apiQ && String(apiQ).trim()) {
                return String(apiQ).trim().replace(/\/+$/, '');
            }
        } catch (_) {}
        try {
            const m = document.querySelector('meta[name="dastyor-api-base"]');
            const c = m && m.getAttribute('content');
            if (c != null && String(c).trim() !== '') {
                return String(c).trim().replace(/\/+$/, '');
            }
        } catch (_) {}
        if (location.protocol === 'file:') {
            return PROD_API_FALLBACK;
        }
        try {
            const o = location.origin;
            if (o && o !== 'null') {
                return String(o).replace(/\/+$/, '');
            }
        } catch (_) {}
        return PROD_API_FALLBACK;
    }

    const BASE = resolveApiBase();
    const THEME_KEY = 'theme';
    const LANGUAGE_KEY = 'language';
    const SS_LANG = 'tg_lang';
    const SUPPORTED_LANGS = ['uz'];
    const DEFAULT_THEME = 'light';
    const DEFAULT_LANG = 'uz';

    /** Inline fallback — avoids failed /locales fetch on cold start (saves ~1 network round-trip). */
    const INLINE_LOCALE_UZ = {
        app_title: 'CV Yaratish',
        step_1: 'Shaxsiy', step_2: 'Tajriba', step_3: 'Yutuqlar',
        upload_img: 'Rasmni tanlang', drag_img: 'yoki rasmni shu yerga tortib tashlang',
        photo_hint: 'JPG yoki PNG (3×4 rasm)',
        name: 'Ism Familiya', name_ph: 'Ali Valiyev',
        role: 'Kasb / Lavozim', role_ph: 'Masalan: Dasturchi',
        phone: 'Telefon', cv_phone_ph: '+998 90 123 45 67',
        email: 'Email', location: 'Manzil (Viloyat, Shahar)', loc_ph: 'Masalan: Toshkent shahri',
        about: 'Men haqimda', about_ph: 'Men haqimda...',
        next_btn: 'Keyingisi', back_btn: 'Orqaga',
        edu_title: "Ta'lim", add_edu: "+ Ta'lim qo'shish",
        exp_title: 'Ish Tajribasi', add_exp: "+ Tajriba qo'shish",
        lang_title: 'Til Bilish', add_lang: "+ Til qo'shish",
        skills_title: "Ko'nikmalar", cv_skills_ph: 'Masalan: Liderlik, Python...',
        ach_title: 'Yutuqlar va Qobiliyatlar', cv_ach_name_ph: 'Nomi (masalan: IELTS 7.5)', cv_year_ph: 'Yili',
        preview: "Jonli Ko'rinish", cv_color: 'Rang:',
        download_pdf: 'PDF botga yuborish', pay_5000: "💳 7 999 so'm to'lash",
        pay_help: "Limit tugasa pastdagi '7 999 so'm to'lash' tugmasi orqali davom etasiz.",
        cv_pay_shot_picked_title: 'Rasm tanlandi', cv_pay_shot_next: "Endi «Yuborish» tugmasini bosing.",
        clear_data: "Ma'lumotlarni tozalash",
        loading: 'Yuklanmoqda...', success: 'Muvaffaqiyatli!',
        error_generic: "Xatolik yuz berdi. Qayta urinib ko'ring.",
        error_network: "Internet aloqasi yo'q. Keyinroq urinib ko'ring.",
        error_auth: 'Avtorizatsiya talab qilinadi. Telegram orqali qayta oching.',
        payment_pending: "Admin to'lovingizni tekshirmoqda...",
        payment_approved: "To'lov tasdiqlandi! Hujjatni yuklab olishingiz mumkin.",
        payment_rejected: "To'lov rad etildi. Qayta urinib ko'ring.",
        demo_watermark_note: "Demo versiya — «DEMO VERSIYA» belgisi bilan. To'lovdan keyin toza fayl.",
        test_download: 'Demo yuklash', test_download_loading: 'Yuklanmoqda...',
    };

    const SS_ID = 'tg_id';
    const SS_TOKEN = 'tg_token';
    const SS_USER = 'tg_user';

    let tg = window.Telegram?.WebApp;
    let user = null;
    let token = null;

    function getUser() {
        return user;
    }
    let currentTheme = DEFAULT_THEME;
    let currentLang = DEFAULT_LANG;
    let localeMap = {};
    const localeCache = {};

    function normalizeLang(lang) {
        const raw = String(lang || '').toLowerCase();
        if (raw === 'uz_lat' || raw === 'uz_cyr') return 'uz';
        if (SUPPORTED_LANGS.includes(raw)) return raw;
        return DEFAULT_LANG;
    }

    function pickLangCandidate(raw) {
        const s = String(raw || '').trim().toLowerCase();
        if (!s) return '';
        if (s === 'uz_lat' || s === 'uz_cyr') return 'uz';
        return SUPPORTED_LANGS.includes(s) ? s : '';
    }

    function normalizeTheme(theme) {
        return String(theme || '').toLowerCase() === 'dark' ? 'dark' : 'light';
    }

    function persistSession(nextUser, nextToken) {
        user = nextUser;
        token = nextToken;
        try {
            sessionStorage.setItem(SS_ID, String(nextUser.telegram_id));
            sessionStorage.setItem(SS_TOKEN, nextToken);
            sessionStorage.setItem(SS_USER, JSON.stringify(nextUser));
        } catch (_) {}
    }

    function restoreSession() {
        try {
            const rawUser = sessionStorage.getItem(SS_USER);
            if (rawUser) user = JSON.parse(rawUser);
            token = sessionStorage.getItem(SS_TOKEN) || null;
        } catch (_) {}
    }

    function readIdentity() {
        const tgUser = tg?.initDataUnsafe?.user;
        if (tgUser?.id) {
            return {
                telegram_id: tgUser.id,
                first_name: tgUser.first_name || '',
                username: tgUser.username || '',
                photo_url: tgUser.photo_url || '',
            };
        }

        const urlId = new URLSearchParams(location.search).get('telegram_id');
        if (urlId && /^\d+$/.test(urlId)) {
            return { telegram_id: parseInt(urlId, 10), first_name: '', username: '', photo_url: '' };
        }

        const ssId = sessionStorage.getItem(SS_ID);
        if (ssId && /^\d+$/.test(ssId)) {
            const ssUser = (() => { try { return JSON.parse(sessionStorage.getItem(SS_USER) || '{}'); } catch (_) { return {}; } })();
            return {
                telegram_id: parseInt(ssId, 10),
                first_name: ssUser.first_name || '',
                username: ssUser.username || '',
                photo_url: ssUser.photo_url || '',
            };
        }
        return null;
    }

    async function apiFetch(path, opts = {}) {
        const headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
        const timeoutMs = Number(opts.timeoutMs) > 0 ? Number(opts.timeoutMs) : 30000;
        const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
        const timer = controller
            ? setTimeout(() => {
                try {
                    controller.abort();
                } catch (_) {}
            }, timeoutMs)
            : null;
        try {
            const fetchOpts = { ...opts, headers };
            if (controller && !fetchOpts.signal) fetchOpts.signal = controller.signal;
            return await fetch(BASE + path, fetchOpts);
        } finally {
            if (timer) clearTimeout(timer);
        }
    }

    async function auth(identity) {
        const body = { ...identity };
        if (tg?.initData) body.init_data = tg.initData;
        const resp = await apiFetch('/api/auth', { method: 'POST', body: JSON.stringify(body) });
        if (!resp.ok) throw new Error(`/api/auth failed: ${resp.status}`);
        return resp.json();
    }

    function syncTelegramColors(theme) {
        const bg = theme === 'dark' ? '#0f0f0f' : '#ffffff';
        tg?.setHeaderColor?.(bg);
        tg?.setBackgroundColor?.(bg);
    }

    function applyTheme(theme, persist = true) {
        currentTheme = normalizeTheme(theme);
        const root = document.documentElement;
        root.setAttribute('data-theme', currentTheme);
        root.classList.toggle('dark', currentTheme === 'dark');
        root.classList.toggle('light', currentTheme === 'light');
        syncTelegramColors(currentTheme);
        if (persist) localStorage.setItem(THEME_KEY, currentTheme);
        window.dispatchEvent(new CustomEvent('app:theme-changed', { detail: { theme: currentTheme } }));
        return currentTheme;
    }

    async function loadLocale(lang) {
        const safe = normalizeLang(lang);
        if (localeCache[safe]) return localeCache[safe];
        try {
            const cached = sessionStorage.getItem(`da_locale_${safe}`);
            if (cached) {
                const parsed = JSON.parse(cached);
                if (parsed && typeof parsed === 'object') {
                    localeCache[safe] = parsed;
                    return parsed;
                }
            }
        } catch (_) {}
        const candidates = [
            `locales/${safe}.json`,
            `/webapp/locales/${safe}.json`,
            `/locales/${safe}.json`,
        ];

        for (const url of candidates) {
            try {
                // Telegram WebView sometimes hangs on fetch; use a short timeout.
                const ac = ('AbortController' in window) ? new AbortController() : null;
                const t = ac ? setTimeout(() => { try { ac.abort(); } catch (_) {} }, 1500) : null;
                const resp = await fetch(url, ac ? { signal: ac.signal } : undefined);
                if (t) clearTimeout(t);
                if (resp.ok) {
                    const data = await resp.json();
                    localeCache[safe] = data || {};
                    try {
                        sessionStorage.setItem(`da_locale_${safe}`, JSON.stringify(localeCache[safe]));
                    } catch (_) {}
                    return localeCache[safe];
                }
            } catch (_) {}
        }
        localeCache[safe] = safe === 'uz' ? { ...INLINE_LOCALE_UZ } : {};
        return localeCache[safe];
    }

    function translate(key, fallback = '') {
        if (!key) return fallback || '';
        const val = localeMap[key];
        if (typeof val === 'string' && val.trim()) return val;
        return fallback || key;
    }

    function applyTranslations(root = document) {
        try {
            if (
                root === document &&
                document.body &&
                document.body.getAttribute('data-da-skip-global-i18n') === '1'
            ) {
                return;
            }
        } catch (_) {}

        const langAttr = currentLang === 'ru' ? 'ru' : currentLang === 'en' ? 'en' : 'uz';

        root.querySelectorAll('[data-i18n]').forEach((el) => {
            const key = el.getAttribute('data-i18n');
            const attr = el.getAttribute('data-i18n-attr');
            const fallback = el.getAttribute('data-i18n-fallback') || el.textContent.trim();
            if (!el.hasAttribute('data-i18n-fallback')) el.setAttribute('data-i18n-fallback', fallback);
            const text = translate(key, fallback);
            if (attr) {
                el.setAttribute(attr, text);
            } else {
                el.textContent = text;
            }
        });

        root.querySelectorAll('[data-i18n-ph]').forEach((el) => {
            const key = el.getAttribute('data-i18n-ph');
            const fallback = el.getAttribute('placeholder') || '';
            el.setAttribute('placeholder', translate(key, fallback));
        });

        try {
            document.documentElement.lang = langAttr;
        } catch (_) {}
        window.dispatchEvent(new CustomEvent('app:language-applied', { detail: { language: currentLang } }));
    }

    async function setLanguage(lang, persist = true) {
        currentLang = normalizeLang(lang);
        try {
            if (persist) {
                localStorage.setItem(LANGUAGE_KEY, currentLang);
                sessionStorage.setItem(SS_LANG, currentLang);
            }
            // Keep current language in URL so reopening this page keeps same language.
            const u = new URL(window.location.href);
            u.searchParams.set('lang', currentLang);
            history.replaceState(null, '', u.toString());
        } catch (_) {}

        // Immediate apply (even if locale fetch is slow/hangs, at least update <html lang> and events)
        try { applyTranslations(document); } catch (_) {}

        try {
            localeMap = await loadLocale(currentLang);
        } catch (_) {
            localeMap = {};
        }
        try { applyTranslations(document); } catch (_) {}
        try {
            window.dispatchEvent(new CustomEvent('app:language-changed', { detail: { language: currentLang } }));
        } catch (_) {}
        return currentLang;
    }

    async function initPreferences() {
        const savedTheme = normalizeTheme(localStorage.getItem(THEME_KEY) || DEFAULT_THEME);
        const urlLang = pickLangCandidate(new URLSearchParams(location.search || '').get('lang'));
        const ssLang = pickLangCandidate(sessionStorage.getItem(SS_LANG));
        const lsLang = pickLangCandidate(localStorage.getItem(LANGUAGE_KEY));
        const savedLang = normalizeLang(urlLang || ssLang || lsLang || DEFAULT_LANG);
        applyTheme(savedTheme, false);
        await setLanguage(savedLang, false);
    }

    function getTelegramId() {
        return user?.telegram_id
            ?? sessionStorage.getItem(SS_ID)
            ?? new URLSearchParams(location.search).get('telegram_id')
            ?? null;
    }

    function _pickTariffFields(obj) {
        const keys = [
            'plan',
            'plan_label',
            'unlimited',
            'daily_limit',
            'used_today',
            'remaining',
            'subscription_ends',
            'limits_breakdown',
            'has_cv_access',
            'has_objective_access',
            'credits',
            'has_access',
            'credit_note',
            // Referral marketing
            'referred_by',
            'referrals_count',
            'referral_discount_percent',
            'referral_discount_active',
            'referral_discount_expires_at',
        ];
        const o = {};
        keys.forEach((k) => {
            if (obj[k] !== undefined && obj[k] !== null) o[k] = obj[k];
        });
        return o;
    }

    function formatPriceUzs(amount) {
        const n = Number(amount || 0);
        if (!n) return '0';
        return n.toLocaleString('fr-FR').replace(/\u202f/g, ' ').replace(/,/g, ' ');
    }

    function docPriceUzs(u) {
        const subject = u || user;
        const p = subject && subject.single_doc_price_uzs;
        return Number(p) > 0 ? Number(p) : 7999;
    }

    function getCredits(u) {
        const subject = u || user;
        if (subject && (subject.credits !== undefined && subject.credits !== null)) {
            return Math.max(0, Number(subject.credits || 0));
        }
        if (subject && subject.has_access === true) {
            return Math.max(1, Number(subject.credits || 0));
        }
        try {
            const raw = sessionStorage.getItem(SS_USER);
            if (raw) {
                const p = JSON.parse(raw);
                return Math.max(0, Number(p.credits || 0));
            }
        } catch (_) {}
        return 0;
    }

    function hasUniversalCredit(u) {
        const subject = u || user;
        if (getCredits(subject) > 0) return true;
        return !!(subject && subject.has_access === true);
    }

    function universalCreditMessage(u, category) {
        const n = getCredits(u || user);
        if (n < 1) return '';
        const price = formatPriceUzs(docPriceUzs(u));
        const cat = String(category || '').toLowerCase();
        const doc =
            cat === 'cv' ? 'PDF (CV)' : cat === 'obyektivka' ? 'Word (Obyektivka)' : 'hujjat';
        if (n === 1) {
            return `💳 Pul bor — 1 ta hujjat (${price} so'm). Hozir ${doc} yaratishingiz mumkin.`;
        }
        return `💳 Pul bor — ${n} ta hujjat (${price} so'mdan). CV yoki Obyektivka yaratishingiz mumkin.`;
    }

    /**
     * Free tarif: CV/obyektivka faqat to'lov (pul balansi) yoki obuna.
     */
    function needsSingleDocPayment(u, category) {
        if (!u || !category) return !hasUniversalCredit(u);
        if (hasUniversalCredit(u)) return false;
        const cat = String(category).toLowerCase();
        if (cat !== 'cv' && cat !== 'obyektivka') return false;
        const plan = String(u.plan || u.user_plan || 'free').toLowerCase();
        if (plan === 'standard' || plan === 'premium') return false;
        if (cat === 'cv' && u.has_cv_access) return false;
        if (cat === 'obyektivka' && u.has_objective_access) return false;
        if (Array.isArray(u.limits_breakdown)) {
            const row = u.limits_breakdown.find((r) => r.category === cat);
            if (row && !row.unlimited && !row.blocked) {
                const rem = row.remaining != null ? Number(row.remaining) : NaN;
                if (!Number.isNaN(rem) && rem <= 0) return true;
            }
        }
        return true;
    }

    /**
     * /api/me limits_breakdown: bu kategoriya uchun limit tugagan yoki to'lov kerak.
     */
    function isQuotaBlockedForCategory(u, category) {
        if (hasUniversalCredit(u)) return false;
        if (!u || !category) return true;
        if (needsSingleDocPayment(u, category)) return true;
        if (!Array.isArray(u.limits_breakdown)) return false;
        const row = u.limits_breakdown.find((r) => r.category === category);
        if (!row) return false;
        if (row.unlimited) return false;
        if (row.blocked) return true;
        if (row.exhausted === true) return true;
        const rem = row.remaining != null ? Number(row.remaining) : NaN;
        if (!Number.isNaN(rem) && rem <= 0) return true;
        return false;
    }

    /** limits_breakdown dan qolgan limit (paid_once uchun 0 = yuborilgan) */
    function getCategoryQuotaRemaining(u, category) {
        if (!u || !category || !Array.isArray(u.limits_breakdown)) return null;
        const row = u.limits_breakdown.find((r) => r.category === category);
        if (!row) return null;
        if (row.unlimited) return Infinity;
        if (row.blocked) return 0;
        if (row.exhausted === true) return 0;
        const rem = row.remaining != null ? Number(row.remaining) : null;
        return rem != null && !Number.isNaN(rem) ? rem : null;
    }

    /** has_cv_access / has_objective_access — admin tasdiqlagan 1 ta yuborish huquqi */
    function hasSingleDocAccess(u, category) {
        if (hasUniversalCredit(u)) return true;
        if (!u || !category) return false;
        const cat = String(category).toLowerCase();
        if (cat === 'cv') return !!u.has_cv_access;
        if (cat === 'obyektivka') return !!u.has_objective_access;
        return false;
    }

    /** To'langan bitta hujjat allaqachon ishlatilgan */
    function isSingleDocLimitExhausted(u, category) {
        if (!u || !category) return false;
        if (hasSingleDocAccess(u, category)) return false;
        const rem = getCategoryQuotaRemaining(u, category);
        if (rem !== null && rem <= 0) return true;
        if (Array.isArray(u.limits_breakdown)) {
            const row = u.limits_breakdown.find((r) => r.category === category);
            if (row && (row.exhausted === true || (row.remaining != null && Number(row.remaining) <= 0))) {
                return true;
            }
        }
        return false;
    }

    function singleDocLimitMessage(category) {
        const cat = String(category || '').toLowerCase();
        const label = cat === 'cv' ? 'CV' : 'Obyektivka';
        return `❌ Limitiz tugagan. Yana ${formatPriceUzs(docPriceUzs())} so'm to'lov qiling (${label}).`;
    }

    /**
     * @param {string} category - plan_limits CAT_* slug (cv, ocr, translate, …)
     * @param {{ warnId?: string, buttonIds?: string[], message?: string }} cfg
     */
    function applyServiceQuotaUi(category, cfg) {
        const u = user && user.telegram_id ? user : null;
        const blocked = isQuotaBlockedForCategory(u, category);
        const msg =
            (cfg && cfg.message) ||
            '⛔ Bu xizmat pullik. Davom etish uchun Premium/Pro tarifni oling.';
        const wid = cfg && cfg.warnId;
        if (wid) {
            const w = document.getElementById(wid);
            if (w) {
                if (blocked) {
                    w.classList.remove('hidden');
                    w.textContent = msg;
                } else {
                    w.classList.add('hidden');
                    w.textContent = '';
                }
            }
        }
        const ids = (cfg && cfg.buttonIds) || [];
        ids.forEach((id) => {
            const b = document.getElementById(id);
            if (b) b.disabled = !!blocked;
        });
        const lockIds = (cfg && cfg.lockIds) || [];
        lockIds.forEach((id) => {
            const el = document.getElementById(id);
            if (!el) return;
            if (blocked) {
                el.classList.add('pointer-events-none', 'opacity-50');
                el.setAttribute('aria-disabled', 'true');
            } else {
                el.classList.remove('pointer-events-none', 'opacity-50');
                el.removeAttribute('aria-disabled');
            }
        });
    }

    function shouldShowTariffStrip() {
        try {
            return document.body && document.body.getAttribute('data-da-show-tariff-strip') === '1';
        } catch (_) {
            return false;
        }
    }

    function renderTariffBanner(subject) {
        if (!shouldShowTariffStrip()) {
            try {
                document.querySelectorAll('#da-tariff-strip').forEach((el) => el.remove());
            } catch (_) {}
            return;
        }
        const u = subject || user;
        try {
            document.querySelectorAll('#da-tariff-strip').forEach((el) => el.remove());
        } catch (_) {}
        if (!u || !u.telegram_id || !u.plan) return;

        let line;
        const br = u.limits_breakdown;
        if (Array.isArray(br) && br.length) {
            const bits = br.map((row) => row.display || row.label || '').filter(Boolean);
            line = `${u.plan_label || u.plan || ''}`;
            if (u.subscription_ends) line += ` · obuna ${u.subscription_ends}`;
            line += ` · ${bits.join(' · ')}`;
            if (line.length > 240) line = `${line.slice(0, 237)}…`;
        } else if (u.unlimited) {
            line = `${u.plan_label || u.plan} · cheksiz`;
            if (u.subscription_ends) line += ` · obuna ${u.subscription_ends}`;
        } else if (u.daily_limit != null && u.used_today != null && u.remaining != null) {
            const rem = Number(u.remaining);
            const tail = rem <= 0 ? ' — ⚠️ limit tugadi' : '';
            line = `${u.plan_label || u.plan} · bugun ${u.used_today}/${u.daily_limit} · qoldi ${u.remaining}${tail}`;
        } else {
            line = `${u.plan_label || u.plan}`;
        }

        const el = document.createElement('div');
        el.id = 'da-tariff-strip';
        el.className = 'da-tariff-strip';
        el.setAttribute('role', 'status');
        el.textContent = line;
        const dark =
            document.documentElement.classList.contains('dark')
            || document.documentElement.getAttribute('data-theme') === 'dark';
        const colors = dark
            ? 'background:rgba(59,130,246,0.22);color:#e2e8f0;border-bottom:1px solid rgba(96,165,250,0.35)'
            : 'background:rgba(37,99,235,0.12);color:#0f172a;border-bottom:1px solid rgba(37,99,235,0.28)';
        el.style.cssText =
            'position:sticky;top:0;left:0;right:0;z-index:10050;width:100%;box-sizing:border-box;'
            + 'padding:8px 12px;font-size:12px;font-weight:600;line-height:1.35;text-align:center;'
            + colors;
        if (document.body) document.body.insertBefore(el, document.body.firstChild);
    }

    let _profileRefreshInFlight = null;
    let _profileRefreshLastAt = 0;
    const PROFILE_REFRESH_MIN_MS = 2800;

    function getAuthExtras() {
        const t =
            token ||
            (() => {
                try {
                    return sessionStorage.getItem(SS_TOKEN);
                } catch (_) {
                    return null;
                }
            })();
        const init_data = (tg && tg.initData) || '';
        const out = {};
        if (t) out.token = t;
        if (init_data) out.init_data = init_data;
        return out;
    }

    async function ensureAuth() {
        const identity = readIdentity();
        if (!identity) return null;

        const verifyToken = async (t) => {
            if (!t) return false;
            try {
                const r = await apiFetch(
                    `/api/me?telegram_id=${identity.telegram_id}&token=${encodeURIComponent(t)}`,
                );
                return r.ok;
            } catch (_) {
                return false;
            }
        };

        let t =
            token ||
            (() => {
                try {
                    return sessionStorage.getItem(SS_TOKEN);
                } catch (_) {
                    return null;
                }
            })();

        if (t && (await verifyToken(t))) {
            token = t;
            return t;
        }

        token = null;
        try {
            sessionStorage.removeItem(SS_TOKEN);
        } catch (_) {}

        const authResp = await auth(identity);
        const profileResp = await apiFetch(
            `/api/me?telegram_id=${identity.telegram_id}&token=${authResp.token}`,
        );
        const profile = profileResp.ok ? await profileResp.json() : {};
        const fullUser = {
            telegram_id: identity.telegram_id,
            first_name: identity.first_name || profile.first_name || '',
            username: identity.username || profile.username || '',
            photo_url: identity.photo_url || profile.photo_url || '',
            is_premium: profile.is_premium ?? false,
            files_processed: profile.files_processed ?? 0,
            joined_at: profile.joined_at || '',
            ..._pickTariffFields(profile),
        };
        persistSession(fullUser, authResp.token);
        if (shouldShowTariffStrip()) renderTariffBanner(fullUser);
        return authResp.token;
    }

    async function init(opts = {}) {
        restoreSession();
        if (tg) {
            tg.ready();
            tg.expand();
        }
        const identity = readIdentity();
        if (!identity) return null;

        if (token && user && String(user.telegram_id) === String(identity.telegram_id)) {
            if (opts.refreshProfile !== false) {
                await refreshProfile(true);
            } else if (shouldShowTariffStrip()) {
                renderTariffBanner(user);
            }
            return user;
        }

        try {
            const authResp = await auth(identity);
            const profileResp = await apiFetch(`/api/me?telegram_id=${identity.telegram_id}&token=${authResp.token}`);
            const profile = profileResp.ok ? await profileResp.json() : {};
            const fullUser = {
                telegram_id: identity.telegram_id,
                first_name: identity.first_name || profile.first_name || '',
                username: identity.username || profile.username || '',
                photo_url: identity.photo_url || profile.photo_url || '',
                is_premium: profile.is_premium ?? false,
                files_processed: profile.files_processed ?? 0,
                joined_at: profile.joined_at || '',
                ..._pickTariffFields(profile),
            };
            persistSession(fullUser, authResp.token);
            if (shouldShowTariffStrip()) renderTariffBanner(fullUser);
            return fullUser;
        } catch (_) {
            user = { ...identity, is_premium: false, files_processed: 0 };
            try {
                const mr = await apiFetch(`/api/me?telegram_id=${identity.telegram_id}`);
                if (mr.ok) Object.assign(user, _pickTariffFields(await mr.json()));
            } catch (e2) { /* ignore */ }
            if (shouldShowTariffStrip()) renderTariffBanner(user);
            return user;
        }
    }

    async function refreshProfile(force = false) {
        const identity = readIdentity();
        if (!identity) return user;
        const now = Date.now();
        if (!force && _profileRefreshInFlight) {
            return _profileRefreshInFlight;
        }
        if (!force && now - _profileRefreshLastAt < PROFILE_REFRESH_MIN_MS && user) {
            return user;
        }

        const run = async () => {
            const t = token || (() => {
                try {
                    return sessionStorage.getItem('tg_token');
                } catch (_) {
                    return null;
                }
            })();
            try {
                if (t) {
                    const r = await apiFetch(
                        `/api/me?telegram_id=${identity.telegram_id}&token=${encodeURIComponent(t)}`,
                    );
                    if (r.ok) {
                        const p = await r.json();
                        if (!user) user = { telegram_id: identity.telegram_id };
                        Object.assign(user, _pickTariffFields(p));
                        persistSession(user, t);
                        token = t;
                    } else if (r.status === 401) {
                        try {
                            await ensureAuth();
                        } catch (_) {
                            /* keep stale user cleared on next export */
                        }
                    }
                } else {
                    try {
                        await ensureAuth();
                    } catch (_) {
                        /* ignore */
                    }
                }
            } catch (_) { /* ignore */ }
            if (shouldShowTariffStrip()) renderTariffBanner(user);
            try {
                window.dispatchEvent(new CustomEvent('dastyor:profile-updated', { detail: user }));
            } catch (_) {}
            _profileRefreshLastAt = Date.now();
            return user;
        };

        _profileRefreshInFlight = run();
        try {
            return await _profileRefreshInFlight;
        } finally {
            _profileRefreshInFlight = null;
        }
    }

    function navigate(page) {
        const tid = getTelegramId();
        const abs = new URL(page, window.location.href);
        if (tid) abs.searchParams.set('telegram_id', tid);
        abs.searchParams.set('lang', currentLang || DEFAULT_LANG);
        location.href = abs.toString();
    }

    async function notify(message) {
        const tid = getTelegramId();
        if (!tid) return;
        try {
            await fetch(BASE + '/api/notify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ telegram_id: parseInt(tid, 10), message, token }),
            });
        } catch (_) {}
    }

    async function stats() {
        const tid = getTelegramId();
        if (!tid) return null;
        try {
            const params = new URLSearchParams({ telegram_id: String(tid) });
            if (token) params.set('token', token);
            const r = await fetch(`${BASE}/api/stats?${params}`);
            return r.ok ? r.json() : null;
        } catch (_) {
            return null;
        }
    }

    function buildFormData(extraFields = {}) {
        const fd = new FormData();
        const tid = getTelegramId();
        if (tid) fd.append('telegram_id', String(tid));
        Object.entries(extraFields).forEach(([k, v]) => fd.append(k, v));
        return fd;
    }

    async function translateText(text, direction) {
        const tid = getTelegramId();
        const tok = token || (() => {
            try {
                return sessionStorage.getItem('tg_token');
            } catch (_) {
                return null;
            }
        })();
        const body = {
            text,
            direction,
            ...(tid && /^\d+$/.test(String(tid))
                ? { telegram_id: parseInt(String(tid), 10), token: tok || null }
                : {}),
        };
        const r = await apiFetch('/api/translate', { method: 'POST', body: JSON.stringify(body) });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || 'Translation failed');
        return data.translated_text;
    }

    async function translit(text, direction) {
        const tid = getTelegramId();
        const tok = token || (() => {
            try {
                return sessionStorage.getItem('tg_token');
            } catch (_) {
                return null;
            }
        })();
        const body = {
            text,
            direction,
            ...(tid && /^\d+$/.test(String(tid))
                ? { telegram_id: parseInt(String(tid), 10), token: tok || null }
                : {}),
        };
        const r = await apiFetch('/api/translit', { method: 'POST', body: JSON.stringify(body) });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || 'Translit failed');
        return data.result;
    }

    function _ensureMobileShell() {
        // CV + Obyektivka only — bottom nav olib tashlangan.
    }

    function _ensureBottomNav() {
        try {
            document.querySelectorAll('.da-bottom-nav, .bottom-nav').forEach((el) => el.remove());
        } catch (_) {}
    }

    function _bindViewportVars() {
        // Helps keep inputs visible with mobile keyboard and avoids layout jumps.
        const apply = () => {
            try {
                const vv = window.visualViewport;
                const h = vv?.height || window.innerHeight;
                document.documentElement.style.setProperty('--app-vh', `${h}px`);
                const kb = vv ? Math.max(0, window.innerHeight - vv.height - (vv.offsetTop || 0)) : 0;
                document.documentElement.style.setProperty('--kb-offset', `${kb}px`);
            } catch (_) {}
        };
        apply();
        window.visualViewport?.addEventListener?.('resize', apply);
        window.visualViewport?.addEventListener?.('scroll', apply);
        window.addEventListener('resize', apply, { passive: true });

        // When focusing inputs on mobile, ensure they stay visible.
        document.addEventListener('focusin', (e) => {
            const t = e.target;
            if (!t) return;
            const tag = String(t.tagName || '').toLowerCase();
            if (tag === 'input' || tag === 'textarea' || tag === 'select') {
                setTimeout(() => {
                    try { t.scrollIntoView({ block: 'center', behavior: 'smooth' }); } catch (_) {}
                }, 50);
            }
        }, true);
    }

    function haptic(type = 'light') {
        if (!tg?.HapticFeedback) return;
        if (['light', 'medium', 'heavy'].includes(type)) tg.HapticFeedback.impactOccurred(type);
        else tg.HapticFeedback.notificationOccurred(type);
    }

    function debounce(fn, waitMs = 400) {
        let timer = null;
        return function debounced(...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), waitMs);
        };
    }

    function throttle(fn, waitMs = 400) {
        let last = 0;
        let trailing = null;
        return function throttled(...args) {
            const now = Date.now();
            const remaining = waitMs - (now - last);
            if (remaining <= 0) {
                last = now;
                fn.apply(this, args);
            } else {
                clearTimeout(trailing);
                trailing = setTimeout(() => {
                    last = Date.now();
                    fn.apply(this, args);
                }, remaining);
            }
        };
    }

    function createDebouncedSaver(saveFn, waitMs = 500) {
        let timer = null;
        return function scheduleSave(...args) {
            clearTimeout(timer);
            timer = setTimeout(() => {
                const run = () => {
                    try {
                        saveFn(...args);
                    } catch (_) {}
                };
                if (typeof requestIdleCallback === 'function') {
                    requestIdleCallback(run, { timeout: 900 });
                } else {
                    run();
                }
            }, waitMs);
        };
    }

    let _toastTimer = null;
    function showToast(message, type = 'success', durationMs = 3200) {
        const text = String(message || '').trim();
        if (!text) return;
        let el = document.getElementById('da-toast-root');
        if (!el) {
            el = document.createElement('div');
            el.id = 'da-toast-root';
            el.setAttribute('role', 'status');
            el.setAttribute('aria-live', 'polite');
            document.body.appendChild(el);
        }
        const kind = type === 'error' ? 'error' : type === 'info' ? 'info' : 'success';
        el.className = `da-toast-${kind}`;
        el.textContent = text.slice(0, 280);
        el.style.display = 'block';
        clearTimeout(_toastTimer);
        try {
            if (kind === 'success') haptic('success');
            else if (kind === 'error') haptic('error');
        } catch (_) {}
        _toastTimer = setTimeout(() => {
            el.style.display = 'none';
        }, durationMs);
    }

    function showDraftSaved(label = 'Saqlandi') {
        let pill = document.getElementById('da-draft-pill');
        if (!pill) {
            pill = document.createElement('div');
            pill.id = 'da-draft-pill';
            pill.className = 'da-draft-pill';
            pill.setAttribute('aria-live', 'polite');
            document.body.appendChild(pill);
        }
        pill.textContent = '✓ ' + label;
        pill.classList.add('is-visible');
        clearTimeout(pill._hideTimer);
        pill._hideTimer = setTimeout(() => pill.classList.remove('is-visible'), 1800);
    }

    function initNetworkBanner() {
        if (document.getElementById('da-network-banner')) return;
        const banner = document.createElement('div');
        banner.id = 'da-network-banner';
        banner.className = 'da-offline-banner';
        banner.hidden = navigator.onLine !== false;
        banner.textContent = translate('error_network', "Internet aloqasi yo'q. Draft mahalliy saqlanadi.");
        document.body.appendChild(banner);
        window.addEventListener('online', () => {
            banner.hidden = true;
            showToast(translate('success', 'Muvaffaqiyatli!'), 'success', 2000);
        });
        window.addEventListener('offline', () => {
            banner.hidden = false;
            showToast(translate('error_network', "Internet aloqasi yo'q"), 'error', 2800);
        });
    }

    function prefetchPage(href) {
        try {
            const url = new URL(href, window.location.href).toString();
            if (document.querySelector(`link[rel="prefetch"][href="${url}"]`)) return;
            const link = document.createElement('link');
            link.rel = 'prefetch';
            link.href = url;
            link.as = 'document';
            document.head.appendChild(link);
        } catch (_) {}
    }

    function bindInstantTapFeedback() {
        if (document.documentElement.dataset.daTapBound === '1') return;
        document.documentElement.dataset.daTapBound = '1';
        document.addEventListener(
            'pointerdown',
            (e) => {
                const el = e.target.closest('button, a.service-card, .btn, [role="button"]');
                if (!el || el.disabled || el.getAttribute('aria-disabled') === 'true') return;
                el.classList.add('da-tap-active');
                haptic('light');
            },
            { passive: true, capture: true }
        );
        document.addEventListener(
            'pointerup',
            (e) => {
                const el = e.target.closest('.da-tap-active');
                if (!el) return;
                setTimeout(() => el.classList.remove('da-tap-active'), 100);
            },
            { passive: true, capture: true }
        );
        document.addEventListener(
            'pointercancel',
            () => {
                document.querySelectorAll('.da-tap-active').forEach((el) => el.classList.remove('da-tap-active'));
            },
            { passive: true, capture: true }
        );
    }

    function bindPrefetchOnHover(selector) {
        document.querySelectorAll(selector).forEach((el) => {
            const href = el.getAttribute('href');
            if (!href || href.startsWith('http')) return;
            const once = () => prefetchPage(href);
            el.addEventListener('mouseenter', once, { once: true, passive: true });
            el.addEventListener('touchstart', once, { once: true, passive: true });
        });
    }

    /** To‘liq ekran: hujjat tayyorlash (CV, obyektivka, PDF, OCR, …) */
    let _docLoadingRef = 0;
    let _docLoadingEl = null;
    const PROGRESS_STEPS = [
        'Audio qabul qilindi',
        'AI tahlil qilmoqda',
        "Ma'lumotlar ajratildi",
        'Hujjat yaratilmoqda',
        'Tayyor',
    ];
    const PROGRESS_STEPS_TEXT = [
        'Matn qabul qilindi',
        'AI tahlil qilmoqda',
        "Ma'lumotlar ajratildi",
        'Formaga yozilmoqda',
        'Tayyor',
    ];
    let _progressMode = 'voice';

    function _injectDocumentLoadingStyles() {
        if (document.getElementById('da-doc-loading-styles')) return;
        const s = document.createElement('style');
        s.id = 'da-doc-loading-styles';
        s.textContent = `
#da-doc-loading-overlay{position:fixed;inset:0;background:rgba(242,246,255,.96);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);display:none;flex-direction:column;justify-content:center;align-items:center;z-index:2147483000;gap:14px;padding:24px;box-sizing:border-box}
#da-doc-loading-overlay.da-doc-loading-visible{display:flex!important}
html.da-doc-loading-lock{overflow:hidden!important}
html.da-doc-loading-lock body{overflow:hidden!important;touch-action:none}
.da-doc-loading-ring{width:50px;height:50px;border:4px solid #bfdbfe;border-top-color:#2563eb;border-radius:50%;animation:daDocLoadingSpin 1s linear infinite;flex-shrink:0}
@keyframes daDocLoadingSpin{to{transform:rotate(360deg)}}
.da-doc-loading-title{font-size:15px;font-weight:700;color:#1558c0;text-align:center;max-width:92vw}
.da-doc-loading-sub{font-size:13px;color:#64748b;max-width:280px;text-align:center;line-height:1.4}
.da-progress-steps{display:flex;flex-direction:column;gap:8px;width:min(320px,92vw);margin-top:4px}
.da-progress-step{display:flex;align-items:center;gap:10px;font-size:13px;font-weight:600;color:#94a3b8;transition:color .15s ease,opacity .15s ease}
.da-progress-step .da-step-dot{width:22px;height:22px;border-radius:50%;border:2px solid #cbd5e1;display:flex;align-items:center;justify-content:center;font-size:11px;flex-shrink:0;background:#fff}
.da-progress-step.is-active{color:#1558c0}
.da-progress-step.is-active .da-step-dot{border-color:#2563eb;background:#eff6ff}
.da-progress-step.is-done{color:#16a34a}
.da-progress-step.is-done .da-step-dot{border-color:#16a34a;background:#f0fdf4;color:#16a34a}
html[data-theme="dark"] #da-doc-loading-overlay{background:rgba(15,23,42,.94)}
html[data-theme="dark"] .da-doc-loading-title{color:#93c5fd}
html[data-theme="dark"] .da-doc-loading-sub{color:#94a3b8}
html[data-theme="dark"] .da-doc-loading-ring{border-color:#334155;border-top-color:#60a5fa}
`;
        document.head.appendChild(s);
    }

    function _activeProgressSteps() {
        return _progressMode === 'text' ? PROGRESS_STEPS_TEXT : PROGRESS_STEPS;
    }

    function _ensureProgressStepsEl() {
        if (!_docLoadingEl) return null;
        let stepsEl = _docLoadingEl.querySelector('.da-progress-steps');
        const labels = _activeProgressSteps();
        if (stepsEl && stepsEl.childElementCount === labels.length) return stepsEl;
        if (stepsEl) stepsEl.remove();
        stepsEl = document.createElement('div');
        stepsEl.className = 'da-progress-steps';
        stepsEl.setAttribute('role', 'list');
        labels.forEach((label, i) => {
            const row = document.createElement('div');
            row.className = 'da-progress-step';
            row.setAttribute('role', 'listitem');
            row.dataset.step = String(i + 1);
            row.innerHTML = '<span class="da-step-dot" aria-hidden="true">' + (i + 1) + '</span><span class="da-step-label"></span>';
            row.querySelector('.da-step-label').textContent = label;
            stepsEl.appendChild(row);
        });
        _docLoadingEl.appendChild(stepsEl);
        return stepsEl;
    }

    function setProgressStep(step, sub) {
        _injectDocumentLoadingStyles();
        const steps = _activeProgressSteps();
        if (!_docLoadingEl) {
            showDocumentLoading(steps[Math.max(0, step - 1)] || 'Jarayon...', sub || '');
        }
        const n = Math.max(1, Math.min(steps.length, Number(step) || 1));
        const titleEl = _docLoadingEl && _docLoadingEl.querySelector('.da-doc-loading-title');
        const subEl = _docLoadingEl && _docLoadingEl.querySelector('.da-doc-loading-sub');
        if (titleEl) titleEl.textContent = steps[n - 1] || 'Jarayon...';
        if (subEl && sub !== undefined) subEl.textContent = sub || '';
        const stepsEl = _ensureProgressStepsEl();
        if (!stepsEl) return;
        stepsEl.querySelectorAll('.da-progress-step').forEach((row) => {
            const s = Number(row.dataset.step || 0);
            row.classList.remove('is-active', 'is-done');
            if (s < n) {
                row.classList.add('is-done');
                const dot = row.querySelector('.da-step-dot');
                if (dot) dot.textContent = '✓';
            } else if (s === n) {
                row.classList.add('is-active');
                const dot = row.querySelector('.da-step-dot');
                if (dot) dot.textContent = String(s);
            } else {
                const dot = row.querySelector('.da-step-dot');
                if (dot) dot.textContent = String(s);
            }
        });
        try { if (tg?.HapticFeedback?.impactOccurred) tg.HapticFeedback.impactOccurred('light'); } catch (_) {}
    }

    function showProgressFlow(mode) {
        _progressMode = mode === 'text' ? 'text' : 'voice';
        const steps = _activeProgressSteps();
        const start = mode === 'doc' ? 4 : 1;
        showDocumentLoading(steps[start - 1], '');
        setProgressStep(start);
    }

    function canExportWithCredit(u) {
        return getCredits(u) > 0;
    }

    /** CV/Obyektivka eksport: pul balansi, kategoriya huquqi yoki obuna limiti */
    function canExportForCategory(u, category) {
        const subject = u || user;
        if (!subject) return false;
        if (Number(subject.credits || 0) > 0) return true;
        if (hasSingleDocAccess(subject, category)) return true;
        const plan = String(subject.plan || subject.user_plan || 'free').toLowerCase();
        if (plan === 'standard' || plan === 'premium') {
            return !isQuotaBlockedForCategory(subject, category);
        }
        return false;
    }

    /** PDF/Word tugmasi: ready | locked (pul yo'q) | waiting (admin/export) */
    function applyExportButtonState(btn, state, kind) {
        if (!btn) return;
        btn.classList.add('da-export-btn');
        btn.classList.remove(
            'da-export-locked',
            'da-export-waiting',
            'da-export-ready-cv',
            'da-export-ready-oby',
        );
        if (state === 'locked') {
            btn.classList.add('da-export-locked');
            btn.setAttribute('aria-disabled', 'true');
            return;
        }
        if (state === 'waiting') {
            btn.classList.add('da-export-waiting');
            btn.setAttribute('aria-disabled', 'true');
            return;
        }
        btn.removeAttribute('aria-disabled');
        btn.classList.add(kind === 'cv' ? 'da-export-ready-cv' : 'da-export-ready-oby');
    }

    async function ensureJpegDataUrl(dataUrl) {
        if (!dataUrl) return dataUrl;
        const s = String(dataUrl);
        if (s.startsWith('data:image/jpeg') || s.startsWith('data:image/jpg')) {
            return compressReceiptDataUrl(s);
        }
        return new Promise((resolve) => {
            const img = new Image();
            img.onload = () => {
                try {
                    const c = document.createElement('canvas');
                    let w = img.width;
                    let h = img.height;
                    const scale = Math.min(1, 1280 / Math.max(w, h, 1));
                    w = Math.max(1, Math.round(w * scale));
                    h = Math.max(1, Math.round(h * scale));
                    c.width = w;
                    c.height = h;
                    c.getContext('2d').drawImage(img, 0, 0, w, h);
                    resolve(c.toDataURL('image/jpeg', 0.82));
                } catch (_) {
                    resolve(s);
                }
            };
            img.onerror = () => resolve(s);
            img.src = s;
        }).then((out) => compressReceiptDataUrl(out));
    }

    function countCvDataFields(data) {
        if (!data || typeof data !== 'object') return 0;
        let n = 0;
        ['name', 'phone', 'email', 'loc', 'spec', 'about', 'birthdate', 'role'].forEach((k) => {
            const v = data[k];
            if (v != null && String(v).trim()) n += 1;
        });
        if (Array.isArray(data.works) && data.works.length) n += 1;
        if (Array.isArray(data.education_list) && data.education_list.length) n += 1;
        if (Array.isArray(data.experience) && data.experience.length) n += 1;
        if (data.skills && String(data.skills).trim()) n += 1;
        return n;
    }

    function countObyDataFields(data) {
        if (!data || typeof data !== 'object') return 0;
        let n = 0;
        const skip = new Set(["yo'q", 'yoq', 'йўқ', 'нет', 'no', 'n/a', '—', '-']);
        const present = (v) => {
            if (v == null) return false;
            if (Array.isArray(v)) return v.length > 0;
            const s = String(v).trim().toLowerCase();
            return !!s && !skip.has(s);
        };
        [
            'fullname', 'birthdate', 'birthplace', 'nation', 'education', 'edu',
            'graduated', 'specialty', 'spec', 'degree', 'scientific_title',
            'languages', 'langs', 'military_rank', 'awards', 'deputy',
        ].forEach((k) => {
            if (present(data[k])) n += 1;
        });
        if (present(data.work_experience) || present(data.works)) n += 1;
        if (present(data.relatives)) n += 1;
        if (present(data.photo_data) || present(data.photo_base64)) n += 1;
        return n;
    }

    function countCvDomFields() {
        let n = 0;
        ['f_name', 'f_role', 'f_phone', 'f_email', 'f_loc', 'f_about', 'f_birth'].forEach((id) => {
            const el = document.getElementById(id);
            const v = el ? String(el.value || '').trim() : '';
            if (v && v !== '+998') n += 1;
        });
        try {
            if (typeof eduData !== 'undefined' && Array.isArray(eduData) && eduData.length) n += 1;
            if (typeof expData !== 'undefined' && Array.isArray(expData) && expData.length) n += 1;
            if (typeof skillsData !== 'undefined' && Array.isArray(skillsData) && skillsData.length) n += 1;
        } catch (_) {}
        return n;
    }

    function countObyDomFields() {
        let n = 0;
        const skip = new Set(["yo'q", 'yoq']);
        const val = (id) => {
            const el = document.getElementById(id);
            const v = el ? String(el.value || '').trim() : '';
            return v && !skip.has(v.toLowerCase());
        };
        [
            'fullname', 'birthdate', 'birthplace', 'nation', 'edu', 'graduated',
            'spec', 'degree', 'scititle', 'langs', 'awards', 'deputy',
        ].forEach((id) => {
            if (val(id)) n += 1;
        });
        try {
            if (document.querySelectorAll('#work-container .work-row').length) n += 1;
            if (typeof relatives !== 'undefined' && Array.isArray(relatives) && relatives.length) n += 1;
            if (typeof photoData !== 'undefined' && photoData) n += 1;
        } catch (_) {}
        return n;
    }

    function voiceFillHasContent(js, kind) {
        if (!js || !js.data || typeof js.data !== 'object') return false;
        const populated = Number(js.populated_fields);
        if (Number.isFinite(populated) && populated > 0) return true;
        return kind === 'cv' ? countCvDataFields(js.data) > 0 : countObyDataFields(js.data) > 0;
    }

    async function pollVoiceJob(pathPrefix, jobId, telegramId, token, onStep, kind) {
        const base = BASE;
        const q = new URLSearchParams();
        if (telegramId) q.set('telegram_id', String(telegramId));
        if (token) q.set('token', token);
        const url = base + '/api/' + pathPrefix + '/' + encodeURIComponent(jobId) + '?' + q.toString();
        for (let i = 0; i < 150; i++) {
            await new Promise((r) => setTimeout(r, i === 0 ? 60 : 180));
            const res = await fetch(url);
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || ('Server ' + res.status));
            }
            const js = await res.json();
            if (js.status === 'running' && typeof onStep === 'function' && js.step) {
                const step = Math.min(2, Number(js.step) || 1);
                onStep(step);
                logProgressStepComplete(step);
            }
            if (js.status === 'done') {
                if (!voiceFillHasContent(js, kind)) {
                    throw new Error("Ma'lumot ajratilmadi — formaga yozilmadi");
                }
                if (typeof onStep === 'function') {
                    onStep(3);
                    logProgressStepComplete(3, "Ma'lumotlar ajratildi");
                }
                return js;
            }
            if (js.status === 'error') throw new Error(js.error || 'Xatolik');
        }
        throw new Error('Vaqt tugadi. Qayta urinib ko\'ring.');
    }

    async function pollObyVoiceJob(jobId, telegramId, token, onStep) {
        return pollVoiceJob('oby_voice_job', jobId, telegramId, token, onStep, 'oby');
    }

    async function pollCvVoiceJob(jobId, telegramId, token, onStep) {
        return pollVoiceJob('cv_voice_job', jobId, telegramId, token, onStep, 'cv');
    }

    function showDocumentLoading(title, sub) {
        _injectDocumentLoadingStyles();
        _docLoadingRef++;
        if (!_docLoadingEl) {
            _docLoadingEl = document.createElement('div');
            _docLoadingEl.id = 'da-doc-loading-overlay';
            _docLoadingEl.setAttribute('role', 'status');
            _docLoadingEl.setAttribute('aria-busy', 'true');
            _docLoadingEl.innerHTML =
                '<div class="da-doc-loading-ring"></div>' +
                '<div class="da-doc-loading-title"></div>' +
                '<div class="da-doc-loading-sub"></div>';
            document.body.appendChild(_docLoadingEl);
        }
        const titleEl = _docLoadingEl.querySelector('.da-doc-loading-title');
        const subEl = _docLoadingEl.querySelector('.da-doc-loading-sub');
        if (titleEl) titleEl.textContent = title || 'Hujjat tayyorlanmoqda...';
        if (subEl) subEl.textContent = sub !== undefined && sub !== null ? sub : 'Iltimos, 10–15 soniya kuting';
        _docLoadingEl.classList.add('da-doc-loading-visible');
        try {
            document.documentElement.classList.add('da-doc-loading-lock');
        } catch (_) {}
    }

    function hideDocumentLoading() {
        _docLoadingRef = Math.max(0, _docLoadingRef - 1);
        if (_docLoadingRef > 0) return;
        if (_docLoadingEl) {
            _docLoadingEl.classList.remove('da-doc-loading-visible');
        }
        try {
            document.documentElement.classList.remove('da-doc-loading-lock');
        } catch (_) {}
        try {
            if (_docLoadingEl) _docLoadingEl.setAttribute('aria-busy', 'false');
        } catch (_) {}
    }

    function forceHideDocumentLoading() {
        _docLoadingRef = 0;
        hideDocumentLoading();
    }

    function logProgressStepComplete(step, label) {
        const n = Number(step) || 0;
        const msg = label ? 'Step ' + n + ' complete: ' + label : 'Step ' + n + ' complete';
        try { console.log('[CV fill]', msg); } catch (_) {}
    }

    /** Chek skrinshoti — yuborishdan oldin siqish (tezroq upload) */
    function compressReceiptDataUrl(dataUrl, maxLen = 320000, maxSide = 1280) {
        return new Promise((resolve) => {
            if (!dataUrl || !String(dataUrl).startsWith('data:image') || dataUrl.length <= maxLen) {
                resolve(dataUrl);
                return;
            }
            const img = new Image();
            img.onload = () => {
                try {
                    const c = document.createElement('canvas');
                    let w = img.width;
                    let h = img.height;
                    const scale = Math.min(1, maxSide / Math.max(w, h, 1));
                    w = Math.max(1, Math.round(w * scale));
                    h = Math.max(1, Math.round(h * scale));
                    c.width = w;
                    c.height = h;
                    const ctx = c.getContext('2d');
                    ctx.drawImage(img, 0, 0, w, h);
                    let out = c.toDataURL('image/jpeg', 0.82);
                    if (out.length > maxLen) out = c.toDataURL('image/jpeg', 0.65);
                    if (out.length > maxLen) out = c.toDataURL('image/jpeg', 0.5);
                    resolve(out);
                } catch (_) {
                    resolve(dataUrl);
                }
            };
            img.onerror = () => resolve(dataUrl);
            img.src = dataUrl;
        });
    }

    async function generateDoc(endpoint, payload, filename) {
        showProgressFlow('doc');
        try {
            const tid = getTelegramId();
            const enriched = {
                ...payload,
                telegram_id: tid ? parseInt(tid, 10) : null,
                ...getAuthExtras(),
            };
            setProgressStep(4, 'PDF/DOCX tayyorlanmoqda...');
            const resp = await fetch(BASE + endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(enriched),
            });
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                throw new Error(err.detail || `Server error (${resp.status})`);
            }
            setProgressStep(5, 'Yuklab olinmoqda...');
            const blob = await resp.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename || 'document.docx';
            document.body.appendChild(a);
            a.click();
            setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 2000);
            return blob;
        } finally {
            hideDocumentLoading();
        }
    }

    async function initUI(options = {}) {
        const { onUser = null, autoNavLinks = true, profileEl = {} } = options;

        await initPreferences();
        _bindViewportVars();
        initNetworkBanner();

        if (autoNavLinks) {
            document.querySelectorAll('a[href]').forEach((a) => {
                const href = a.getAttribute('href');
                if (href && !href.startsWith('http') && !href.startsWith('//') && !href.startsWith('#')) {
                    if (a.dataset.keepNativeNav === 'true') return;
                    a._daNavHandler && a.removeEventListener('click', a._daNavHandler);
                    a._daNavHandler = (e) => { e.preventDefault(); navigate(href); };
                    a.addEventListener('click', a._daNavHandler);
                }
            });
        }

        const me = await init();
        applyTranslations(document);
        _ensureBottomNav();

        if (!me) return null;
        const { avatarId, nameId, initialsId } = profileEl;
        if (nameId) {
            const el = document.getElementById(nameId);
            if (el) el.textContent = me.first_name || 'User';
        }
        if (initialsId) {
            const el = document.getElementById(initialsId);
            if (el && me.first_name) el.textContent = me.first_name.charAt(0).toUpperCase();
        }
        if (avatarId && me.photo_url) {
            const el = document.getElementById(avatarId);
            if (el) el.innerHTML = `<img src="${me.photo_url}" style="width:100%;height:100%;object-fit:cover" referrerpolicy="no-referrer">`;
        }
        if (onUser) onUser(me);
        return me;
    }

    // Sync across tabs/pages
    window.addEventListener('storage', (e) => {
        if (e.key === THEME_KEY) applyTheme(e.newValue || DEFAULT_THEME, false);
        if (e.key === LANGUAGE_KEY) setLanguage(e.newValue || DEFAULT_LANG, false);
    });

    /** To‘lov holati — forma yopiq bo‘lsa ham (visibility) va qayta ochganda tekshiriladi */
    const _paidDocWatchers = {};

    function paidDocNotifyKey(kind, requestId, status) {
        return `paid_notify_${kind}_${requestId}_${status}`;
    }

    function clearPaidRequestId(storageKey) {
        if (!storageKey) return;
        try {
            localStorage.removeItem(storageKey);
        } catch (_) {}
    }

    async function fetchPaidDocStatus(requestId, storageKey) {
        const tid = getTelegramId();
        const rid = Number(requestId || 0);
        if (!tid || !rid) return null;
        const params = new URLSearchParams({
            request_id: String(rid),
            telegram_id: String(parseInt(tid, 10)),
        });
        if (token) params.set('token', token);
        try {
            const r = await fetch(`${BASE}/api/paid_doc_status?${params}`, { cache: 'no-store' });
            if (r.status === 404) {
                clearPaidRequestId(storageKey);
                return { status: 'not_found', stale: true };
            }
            return r.ok ? r.json() : null;
        } catch (_) {
            return null;
        }
    }

    const PAID_DOC_TERMINAL_STATUSES = new Set(['rejected', 'completed', 'cancelled']);

    function showPaymentResultPopup(kind, status) {
        const label = kind === 'cv' ? 'CV (PDF)' : 'Obyektivka (Word)';
        let message = '';
        if (status === 'approved') {
            message = `✅ To'lov OK.\n«Botga yuborish» tugmasi.`;
        } else if (status === 'rejected') {
            message = `❌ Rad etildi. Qayta skrinshot yoki 🆘 Murojaat.`;
        } else if (status === 'completed') {
            message = `📦 Bu to'lov ishlatilgan. Yangi ${label} — yangi to'lov.`;
        }
        if (!message) return;
        try {
            haptic('success');
        } catch (_) {}
        try {
            if (tg && typeof tg.showPopup === 'function') {
                tg.showPopup({
                    title: 'Dastyor AI',
                    message,
                    buttons: [{ type: 'ok' }],
                });
                return;
            }
        } catch (_) {}
        try {
            if (tg && typeof tg.showAlert === 'function') {
                tg.showAlert(message);
                return;
            }
        } catch (_) {}
        alert(message);
    }

    async function releaseExportPending(category) {
        const cat = category === 'obyektivka' ? 'obyektivka' : 'cv';
        const tid = getTelegramId();
        if (!tid) return false;
        const params = new URLSearchParams({
            category: cat,
            telegram_id: String(parseInt(tid, 10)),
        });
        if (token) params.set('token', token);
        try {
            const r = await fetch(`${BASE}/api/export_release_pending?${params}`, {
                method: 'POST',
                cache: 'no-store',
            });
            return r.ok;
        } catch (_) {
            return false;
        }
    }

    async function processPaidDocStatus(kind, requestId, status, callbacks = {}) {
        const st = String(status || '').toLowerCase();
        const rid = Number(requestId || 0);
        if (!rid) return st;
        const cat = kind === 'obyektivka' ? 'obyektivka' : 'cv';

        if (st === 'approved' || st === 'delivered') {
            if (callbacks.onApproved) await callbacks.onApproved(rid, st);
            try {
                await refreshProfile(true);
            } catch (_) {}
            try {
                await releaseExportPending(cat);
            } catch (_) {}
            const u = getUser();
            const paidOk = hasSingleDocAccess(u, cat);
            if (!paidOk) {
                return st;
            }
            const nk = paidDocNotifyKey(kind, rid, 'approved');
            if (!callbacks.silent && localStorage.getItem(nk) !== '1') {
                localStorage.setItem(nk, '1');
                showPaymentResultPopup(kind, 'approved');
                window.dispatchEvent(
                    new CustomEvent('dastyor:payment-approved', {
                        detail: { kind, requestId: rid, status: st },
                    }),
                );
            }
        } else if (st === 'rejected') {
            if (callbacks.onRejected) await callbacks.onRejected(rid, st);
            const nk = paidDocNotifyKey(kind, rid, 'rejected');
            if (localStorage.getItem(nk) !== '1') {
                localStorage.setItem(nk, '1');
                showPaymentResultPopup(kind, 'rejected');
                window.dispatchEvent(
                    new CustomEvent('dastyor:payment-rejected', { detail: { kind, requestId: rid } }),
                );
            }
        } else if (st === 'completed') {
            if (callbacks.onCompleted) await callbacks.onCompleted(rid, st);
            const nk = paidDocNotifyKey(kind, rid, 'completed');
            if (!callbacks.silent) {
                localStorage.setItem(nk, '1');
            }
        }
        return st;
    }

    function stopPaidDocWatcher(kind) {
        const w = _paidDocWatchers[kind];
        if (!w) return;
        clearInterval(w.timer);
        if (w.onVis) document.removeEventListener('visibilitychange', w.onVis);
        delete _paidDocWatchers[kind];
    }

    function startPaidDocWatcher(opts = {}) {
        const kind = opts.kind === 'obyektivka' ? 'obyektivka' : 'cv';
        const storageKey =
            opts.storageKey || (kind === 'cv' ? 'cv_paid_request_id' : 'oby_paid_request_id');
        const intervalMs = Number(opts.intervalMs) > 0 ? Number(opts.intervalMs) : 2500;

        stopPaidDocWatcher(kind);

        const tick = async () => {
            let rid = 0;
            try {
                rid = Number(localStorage.getItem(storageKey) || 0);
            } catch (_) {}
            if (!rid && typeof opts.getRequestId === 'function') {
                rid = Number(opts.getRequestId() || 0);
            }
            if (!rid) return;
            const js = await fetchPaidDocStatus(rid, storageKey);
            if (!js) return;
            if (js.stale) {
                stopPaidDocWatcher(kind);
                return;
            }
            if (!js.status) return;
            const st = String(js.status || '').toLowerCase();
            await processPaidDocStatus(kind, rid, js.status, opts);
            if (PAID_DOC_TERMINAL_STATUSES.has(st)) {
                stopPaidDocWatcher(kind);
                return;
            }
            if (st === 'approved' || st === 'delivered') {
                const cat = kind === 'obyektivka' ? 'obyektivka' : 'cv';
                if (hasSingleDocAccess(getUser(), cat)) {
                    stopPaidDocWatcher(kind);
                }
            }
        };

        tick();
        const timer = setInterval(tick, intervalMs);
        const onVis = () => {
            if (document.visibilityState === 'visible') tick();
        };
        document.addEventListener('visibilitychange', onVis);
        _paidDocWatchers[kind] = { timer, onVis, storageKey, opts };
    }

    function resumePaidDocWatcher(opts = {}) {
        const storageKey =
            opts.storageKey ||
            (opts.kind === 'obyektivka' ? 'oby_paid_request_id' : 'cv_paid_request_id');
        let rid = 0;
        try {
            rid = Number(localStorage.getItem(storageKey) || 0);
        } catch (_) {}
        if (rid) startPaidDocWatcher(opts);
    }

    const api = {
        ensureAuth,
        getAuthExtras,
        init,
        initUI,
        renderTariffBanner,
        refreshProfile,
        formatPriceUzs,
        docPriceUzs,
        getCredits,
        canExportWithCredit,
        canExportForCategory,
        applyExportButtonState,
        hasUniversalCredit,
        universalCreditMessage,
        isQuotaBlockedForCategory,
        hasSingleDocAccess,
        isSingleDocLimitExhausted,
        singleDocLimitMessage,
        getCategoryQuotaRemaining,
        needsSingleDocPayment,
        applyServiceQuotaUi,
        shouldShowTariffStrip,
        getUser,
        getToken: () => token,
        getTelegramId,
        navigate,
        notify,
        stats,
        buildFormData,
        translate: translateText,
        translit,
        generateDoc,
        haptic,
        showToast,
        showDraftSaved,
        debounce,
        throttle,
        createDebouncedSaver,
        prefetchPage,
        bindPrefetchOnHover,
        bindInstantTapFeedback,
        initNetworkBanner,
        showDocumentLoading,
        hideDocumentLoading,
        forceHideDocumentLoading,
        logProgressStepComplete,
        setProgressStep,
        showProgressFlow,
        pollObyVoiceJob,
        pollCvVoiceJob,
        countCvDataFields,
        countObyDataFields,
        countCvDomFields,
        countObyDomFields,
        voiceFillHasContent,
        ensureJpegDataUrl,
        PROGRESS_STEPS,
        compressReceiptDataUrl,

        fetchPaidDocStatus,
        processPaidDocStatus,
        releaseExportPending,
        startPaidDocWatcher,
        stopPaidDocWatcher,
        resumePaidDocWatcher,
        showPaymentResultPopup,

        // Theme API
        applyTheme,
        setTheme: (theme) => applyTheme(theme, true),
        toggleTheme: () => applyTheme(currentTheme === 'dark' ? 'light' : 'dark', true),
        getTheme: () => currentTheme,

        // Language API
        setLanguage: (lang) => setLanguage(lang, true),
        getLanguage: () => currentLang,
        t: translate,
        applyTranslations,
        getSupportedLanguages: () => [...SUPPORTED_LANGS],

        get tg() { return tg; },
        get BASE() { return BASE; },
    };

    // Backward-compat bridge
    window.I18n = {
        t: (key) => api.t(key, key),
        getLang: () => api.getLanguage(),
        setLang: (lang) => api.setLanguage(lang),
        apply: () => api.applyTranslations(document),
        showPicker: () => {},
    };

    // Legacy DA bridge (previously provided by da-core.js)
    if (!window.DA) {
        window.DA = {
            t: (key) => api.t(key, key),
            getLang: () => api.getLanguage(),
            setLang: (lang) => api.setLanguage(lang),
            getTheme: () => api.getTheme(),
            setTheme: (theme) => api.setTheme(theme),
            iconSvg: () => '',
        };
    }

    // Early apply (before page scripts run)
    applyTheme(localStorage.getItem(THEME_KEY) || DEFAULT_THEME, false);
    // Til: loadLocale asinxron — DOM bo‘lmasa yoki keyinroq CV parse bo‘lsa, applyTranslations noto‘g‘ri yozardi.
    (function bootLanguageWhenDomReady() {
        const run = () => {
            if (document.body && document.body.dataset.daSkipGlobalI18n === '1') {
                return;
            }
            const qsLang = pickLangCandidate(new URLSearchParams(location.search || '').get('lang'));
            const ssLang = pickLangCandidate(sessionStorage.getItem(SS_LANG));
            const lsLang = pickLangCandidate(localStorage.getItem(LANGUAGE_KEY));
            void setLanguage(qsLang || ssLang || lsLang || DEFAULT_LANG, false);
        };
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', run, { once: true });
        } else {
            run();
        }
    })();

    // Ensure bottom nav exists even if a page forgets to call initUI().
    const _bootMobile = () => {
        try {
            _bindViewportVars();
            initNetworkBanner();
            bindInstantTapFeedback();
            _ensureBottomNav();
            bindPrefetchOnHover('a.service-card, a[href$="cv.html"], a[href*="obyektivka.html"]');
        } catch (_) {}
    };
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _bootMobile, { once: true });
    } else {
        _bootMobile();
    }

    return api;
})();

try {
    window.DastyorAI = DastyorAI;
} catch (_) {}
