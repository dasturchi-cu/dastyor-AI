/**
 * DASTYOR AI — Global WebApp SDK
 * - Auth/session API helpers
 * - Global theme (light/dark)
 * - Global i18n (uz/ru/en from /locales/*.json)
 */
const DastyorAI = (() => {
    'use strict';

    const BASE = location.protocol === 'file:' ? 'https://dastyor-ai.onrender.com' : location.origin;
    const THEME_KEY = 'theme';
    const LANGUAGE_KEY = 'language';
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
        const candidates = [
            `locales/${safe}.json`,
            `/webapp/locales/${safe}.json`,
            `/locales/${safe}.json`,
        ];

        for (const url of candidates) {
            try {
                const resp = await fetch(url, { cache: 'no-store' });
                if (resp.ok) {
                    const data = await resp.json();
                    localeCache[safe] = data || {};
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

        const langAttr = currentLang === 'ru' ? 'ru' : currentLang === 'en' ? 'en' : 'uz';
        document.documentElement.lang = langAttr;
        window.dispatchEvent(new CustomEvent('app:language-applied', { detail: { language: currentLang } }));
    }

    async function setLanguage(lang, persist = true) {
        currentLang = normalizeLang(lang);
        if (persist) localStorage.setItem(LANGUAGE_KEY, currentLang);
        localeMap = await loadLocale(currentLang);
        applyTranslations(document);
        window.dispatchEvent(new CustomEvent('app:language-changed', { detail: { language: currentLang } }));
        return currentLang;
    }

    async function initPreferences() {
        const savedTheme = normalizeTheme(localStorage.getItem(THEME_KEY) || DEFAULT_THEME);
        const savedLang = normalizeLang(localStorage.getItem(LANGUAGE_KEY) || DEFAULT_LANG);
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
        const keys = ['plan', 'plan_label', 'unlimited', 'daily_limit', 'used_today', 'remaining', 'subscription_ends'];
        const o = {};
        keys.forEach((k) => {
            if (obj[k] !== undefined && obj[k] !== null) o[k] = obj[k];
        });
        return o;
    }

    function renderTariffBanner(subject) {
        const u = subject || user;
        try {
            document.querySelectorAll('#da-tariff-strip').forEach((el) => el.remove());
        } catch (_) {}
        if (!u || !u.telegram_id || !u.plan) return;

        let line;
        if (u.unlimited) {
            line = `${u.plan_label || u.plan} · cheksiz`;
            if (u.subscription_ends) line += ` · obuna ${u.subscription_ends}`;
        } else if (u.daily_limit != null && u.used_today != null && u.remaining != null) {
            line = `${u.plan_label || u.plan} · bugun ${u.used_today}/${u.daily_limit} · qoldi ${u.remaining}`;
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

    async function init() {
        restoreSession();
        if (tg) {
            tg.ready();
            tg.expand();
        }
        const identity = readIdentity();
        if (!identity) return null;

        if (token && user && String(user.telegram_id) === String(identity.telegram_id)) {
            renderTariffBanner(user);
            void (async () => {
                try {
                    const r = await apiFetch(
                        `/api/me?telegram_id=${identity.telegram_id}&token=${encodeURIComponent(token)}`,
                    );
                    if (r.ok) {
                        const p = await r.json();
                        Object.assign(user, _pickTariffFields(p));
                        persistSession(user, token);
                        renderTariffBanner(user);
                    }
                } catch (_) { /* ignore */ }
            })();
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
            renderTariffBanner(fullUser);
            return fullUser;
        } catch (_) {
            user = { ...identity, is_premium: false, files_processed: 0 };
            try {
                const mr = await apiFetch(`/api/me?telegram_id=${identity.telegram_id}`);
                if (mr.ok) Object.assign(user, _pickTariffFields(await mr.json()));
            } catch (e2) { /* ignore */ }
            renderTariffBanner(user);
            return user;
        }
    }

    function navigate(page) {
        const tid = getTelegramId();
        const abs = new URL(page, window.location.href);
        if (tid) abs.searchParams.set('telegram_id', tid);
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
        const r = await apiFetch('/api/translate', { method: 'POST', body: JSON.stringify({ text, direction }) });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || 'Translation failed');
        return data.translated_text;
    }

    async function translit(text, direction) {
        const r = await apiFetch('/api/translit', { method: 'POST', body: JSON.stringify({ text, direction }) });
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

    async function generateDoc(endpoint, payload, filename) {
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

    const api = {
        init,
        initUI,
        renderTariffBanner,
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
    setLanguage(localStorage.getItem(LANGUAGE_KEY) || DEFAULT_LANG, false);

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
