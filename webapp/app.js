/**
 * DASTYOR AI — Global WebApp SDK
 * - Auth/session API helpers
 * - Global theme (light/dark)
 * - Global i18n (uz/ru/en from /locales/*.json)
 */
const DastyorAI = (() => {
    'use strict';

    /**
     * API bazasi: avvalo ?api=, keyin meta[name=dastyor-api-base], keyin joriy origin.
     * Railway / boshqa hostda Render ga «qolib ketmasin».
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
            return 'https://dastyor-ai.onrender.com';
        }
        try {
            const o = location.origin;
            if (o && o !== 'null') {
                return String(o).replace(/\/+$/, '');
            }
        } catch (_) {}
        return 'https://dastyor-ai.onrender.com';
    }

    const BASE = resolveApiBase();
    const THEME_KEY = 'theme';
    const LANGUAGE_KEY = 'language';
    const SS_LANG = 'tg_lang';
    const SUPPORTED_LANGS = ['uz', 'ru', 'en'];
    const DEFAULT_THEME = 'light';
    const DEFAULT_LANG = 'uz';

    const SS_ID = 'tg_id';
    const SS_TOKEN = 'tg_token';
    const SS_USER = 'tg_user';

    let tg = window.Telegram?.WebApp;
    let user = null;
    let token = null;
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
        return fetch(BASE + path, { ...opts, headers });
    }

    async function auth(identity) {
        const resp = await apiFetch('/api/auth', { method: 'POST', body: JSON.stringify(identity) });
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
                const t = ac ? setTimeout(() => { try { ac.abort(); } catch (_) {} }, 3000) : null;
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
        localeCache[safe] = {};
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

    /**
     * Free tarif: CV/obyektivka faqat 5 000 so'm (admin tasdiq) yoki obuna.
     */
    function needsSingleDocPayment(u, category) {
        if (!u || !category) return true;
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
        if (!u || !category) return false;
        const cat = String(category).toLowerCase();
        if (cat === 'cv') return !!u.has_cv_access;
        if (cat === 'obyektivka') return !!u.has_objective_access;
        return false;
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
                    }
                } else {
                    const r = await apiFetch(`/api/me?telegram_id=${identity.telegram_id}`);
                    if (r.ok) {
                        const p = await r.json();
                        if (!user) user = { telegram_id: identity.telegram_id };
                        Object.assign(user, _pickTariffFields(p));
                        try {
                            sessionStorage.setItem(SS_USER, JSON.stringify(user));
                        } catch (_) {}
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

    function _navIcon(name) {
        const common = 'fill="none" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"';
        if (name === 'home') return `<svg ${common}><path d="M3 10.5 12 3l9 7.5"/><path d="M5 10v10h14V10"/></svg>`;
        if (name === 'tools') return `<svg ${common}><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>`;
        if (name === 'translate') return `<svg ${common}><path d="M5 8h10"/><path d="M10 5v3c0 4-2.5 6.5-5 8"/><path d="M10 13l3 6 3-6"/><path d="M16 13h4"/></svg>`;
        if (name === 'settings') return `<svg ${common}><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-1.8-.3 1.6 1.6 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.6 1.6 0 0 0-1-1.5 1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 0 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0 .3-1.8 1.6 1.6 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.6 1.6 0 0 0 1.5-1 1.6 1.6 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3h.1a1.6 1.6 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.6 1.6 0 0 0 1 1.5h.1a1.6 1.6 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8v.1a1.6 1.6 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1z"/></svg>`;
        return '';
    }

    function _activeNavKey() {
        const path = location.pathname.toLowerCase();
        if (path.endsWith('/index.html') || path === '/' || path.endsWith('/')) return 'home';
        if (path.endsWith('/more.html')) return 'tools';
        if (path.endsWith('/translate.html')) return 'translate';
        return 'settings';
    }

    function _ensureMobileShell() {
        const body = document.body;
        if (!body) return;
        if (body.dataset.disableMobileNav === 'true') return;
        body.classList.add('da-mobile-shell');
    }

    function _ensureBottomNav() {
        _ensureMobileShell();
        const body = document.body;
        if (!body) return;
        if (body.dataset.disableMobileNav === 'true') return;
        if (document.querySelector('.da-bottom-nav') || document.querySelector('.bottom-nav')) return;

        const active = _activeNavKey();
        const nav = document.createElement('nav');
        nav.className = 'da-bottom-nav';
        nav.innerHTML = `
          <a class="da-nav-item ${active === 'home' ? 'active' : ''}" href="index.html">
            ${_navIcon('home')}
            <span>${translate('tabHome', 'Bosh sahifa')}</span>
          </a>
          <a class="da-nav-item ${active === 'tools' ? 'active' : ''}" href="more.html">
            ${_navIcon('tools')}
            <span>${translate('nav_tools', 'Asboblar')}</span>
          </a>
          <a class="da-nav-item ${active === 'translate' ? 'active' : ''}" href="translate.html">
            ${_navIcon('translate')}
            <span>${translate('nav_translator', 'Tarjimon')}</span>
          </a>
          <a class="da-nav-item ${active === 'settings' ? 'active' : ''}" href="index.html?open=settings">
            ${_navIcon('settings')}
            <span>${translate('nav_settings', 'Sozlamalar')}</span>
          </a>
        `;
        body.appendChild(nav);
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

    /** To‘liq ekran: hujjat tayyorlash (CV, obyektivka, PDF, OCR, …) */
    let _docLoadingRef = 0;
    let _docLoadingEl = null;

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
html[data-theme="dark"] #da-doc-loading-overlay{background:rgba(15,23,42,.94)}
html[data-theme="dark"] .da-doc-loading-title{color:#93c5fd}
html[data-theme="dark"] .da-doc-loading-sub{color:#94a3b8}
html[data-theme="dark"] .da-doc-loading-ring{border-color:#334155;border-top-color:#60a5fa}
`;
        document.head.appendChild(s);
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

    async function generateDoc(endpoint, payload, filename) {
        showDocumentLoading('Yuborilmoqda...', 'Bitta marta bosing');
        try {
            const tid = getTelegramId();
            const enriched = { ...payload, telegram_id: tid ? parseInt(tid, 10) : null, token: token || undefined };
            const resp = await fetch(BASE + endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(enriched),
            });
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                throw new Error(err.detail || `Server error (${resp.status})`);
            }
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

    async function fetchPaidDocStatus(requestId) {
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
            return r.ok ? r.json() : null;
        } catch (_) {
            return null;
        }
    }

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

    async function processPaidDocStatus(kind, requestId, status, callbacks = {}) {
        const st = String(status || '').toLowerCase();
        const rid = Number(requestId || 0);
        if (!rid) return st;

        if (st === 'approved' || st === 'delivered') {
            if (callbacks.onApproved) await callbacks.onApproved(rid, st);
            const nk = paidDocNotifyKey(kind, rid, 'approved');
            if (localStorage.getItem(nk) !== '1') {
                localStorage.setItem(nk, '1');
                try {
                    await refreshProfile();
                } catch (_) {}
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
            if (localStorage.getItem(nk) !== '1') {
                localStorage.setItem(nk, '1');
                showPaymentResultPopup(kind, 'completed');
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
            const js = await fetchPaidDocStatus(rid);
            if (!js || !js.status) return;
            await processPaidDocStatus(kind, rid, js.status, opts);
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
        init,
        initUI,
        renderTariffBanner,
        refreshProfile,
        isQuotaBlockedForCategory,
        hasSingleDocAccess,
        getCategoryQuotaRemaining,
        needsSingleDocPayment,
        applyServiceQuotaUi,
        shouldShowTariffStrip,
        getUser: () => user,
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
        showDocumentLoading,
        hideDocumentLoading,

        fetchPaidDocStatus,
        processPaidDocStatus,
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
            _ensureBottomNav();
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
