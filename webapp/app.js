/**
 * DASTYOR AI — Unified WebApp SDK  (webapp/app.js)
 * ──────────────────────────────────────────────────
 * Single source of truth for all frontend ↔ backend identity + API calls.
 *
 * Usage (in every HTML page, AFTER the Telegram SDK):
 *
 *   <script src="app.js"></script>
 *   <script>
 *     DastyorAI.init().then(user => {
 *       console.log(user.first_name, user.is_premium);
 *     });
 *   </script>
 *
 * What it does:
 *   1. Reads Telegram identity from tg.initDataUnsafe.user  (primary)
 *   2. Falls back to ?telegram_id= URL param                (legacy)
 *   3. Falls back to sessionStorage                         (cross-page)
 *   4. Calls /api/auth to exchange identity → secure token
 *   5. Stores token + user in sessionStorage for all pages
 *   6. Exposes DastyorAI.api.*  helpers for every endpoint
 */

const DastyorAI = (() => {
    'use strict';

    // ── Configuration ────────────────────────────────────────────────────
    const _BASE = (() => {
        if (location.protocol === 'file:') return 'https://dastyor-ai.onrender.com';
        return location.origin;                // same server always
    })();

    const _SS_KEY_ID    = 'tg_id';
    const _SS_KEY_TOKEN = 'tg_token';
    const _SS_KEY_USER  = 'tg_user';

    // ── State ────────────────────────────────────────────────────────────
    let _user  = null;   // { telegram_id, first_name, username, photo_url, is_premium, ... }
    let _token = null;   // server session token
    let _tg    = window.Telegram?.WebApp;

    // ── Private: persist ────────────────────────────────────────────────
    function _persist(user, token) {
        _user  = user;
        _token = token;
        try {
            sessionStorage.setItem(_SS_KEY_ID,    String(user.telegram_id));
            sessionStorage.setItem(_SS_KEY_TOKEN, token);
            sessionStorage.setItem(_SS_KEY_USER,  JSON.stringify(user));
        } catch (_) {}
    }

    // ── Private: restore from storage ───────────────────────────────────
    function _restore() {
        try {
            const raw = sessionStorage.getItem(_SS_KEY_USER);
            if (raw) _user = JSON.parse(raw);
            _token = sessionStorage.getItem(_SS_KEY_TOKEN) || null;
        } catch (_) {}
    }

    // ── Private: fetch wrapper with auto-token injection ─────────────────
    async function _fetch(path, opts = {}) {
        const url = _BASE + path;
        const headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
        // For GET requests that accept params: inject token automatically
        return fetch(url, { ...opts, headers });
    }

    // ── Private: call /api/auth ──────────────────────────────────────────
    async function _auth(identity) {
        const resp = await _fetch('/api/auth', {
            method: 'POST',
            body: JSON.stringify(identity),
        });
        if (!resp.ok) throw new Error(`/api/auth failed: ${resp.status}`);
        return resp.json();   // { ok, token, telegram_id }
    }

    // ── Private: resolve raw identity before auth ───────────────────────
    function _readIdentity() {
        // 1. Telegram WebApp (most reliable in Mini App context)
        const u = _tg?.initDataUnsafe?.user;
        if (u?.id) {
            return {
                telegram_id : u.id,
                first_name  : u.first_name || '',
                username    : u.username   || '',
                photo_url   : u.photo_url  || '',
            };
        }

        // 2. URL param ?telegram_id=
        const urlId = new URLSearchParams(location.search).get('telegram_id');
        if (urlId && /^\d+$/.test(urlId)) {
            return { telegram_id: parseInt(urlId, 10), first_name: '', username: '', photo_url: '' };
        }

        // 3. sessionStorage (cross-page fallback)
        const ssId = sessionStorage.getItem(_SS_KEY_ID);
        if (ssId && /^\d+$/.test(ssId)) {
            const ssUser = (() => { try { return JSON.parse(sessionStorage.getItem(_SS_KEY_USER) || '{}'); } catch(_) { return {}; } })();
            return {
                telegram_id : parseInt(ssId, 10),
                first_name  : ssUser.first_name || '',
                username    : ssUser.username   || '',
                photo_url   : ssUser.photo_url  || '',
            };
        }

        return null;  // anonymous / no identity
    }

    // ═══════════════════════════════════════════════════════════════════
    // PUBLIC API
    // ═══════════════════════════════════════════════════════════════════

    /**
     * init() — MUST be called once per page on DOMContentLoaded.
     * Returns the user object (or null if Telegram ID is unavailable).
     */
    async function init() {
        // Quick restore from storage (instant, sync)
        _restore();

        // Telegram SDK setup
        if (_tg) {
            _tg.ready();
            _tg.expand();
        }

        const identity = _readIdentity();
        if (!identity) {
            console.warn('[DastyorAI] No Telegram identity found — running in guest mode');
            return null;
        }

        // Already have a valid token → re-use
        if (_token && _user && String(_user.telegram_id) === String(identity.telegram_id)) {
            return _user;
        }

        // Exchange identity for server token
        try {
            const authResp = await _auth(identity);
            // After auth, fetch full profile
            const profileResp = await _fetch(`/api/me?telegram_id=${identity.telegram_id}&token=${authResp.token}`);
            const profile = profileResp.ok ? await profileResp.json() : {};
            const user = {
                telegram_id    : identity.telegram_id,
                first_name     : identity.first_name  || profile.first_name  || '',
                username       : identity.username    || profile.username    || '',
                photo_url      : identity.photo_url   || profile.photo_url   || '',
                is_premium     : profile.is_premium   ?? false,
                files_processed: profile.files_processed ?? 0,
                joined_at      : profile.joined_at    || '',
            };
            _persist(user, authResp.token);
            return user;
        } catch (err) {
            console.warn('[DastyorAI] Auth failed, falling back to identity only:', err);
            // Graceful fallback — still functional without server token
            _user = { ...identity, is_premium: false, files_processed: 0 };
            return _user;
        }
    }

    /** Return current user synchronously (null if not yet init'd). */
    function getUser() { return _user; }

    /** Return current session token (null if not authenticated). */
    function getToken() { return _token; }

    /** Return telegram_id string from any available source. */
    function getTelegramId() {
        return _user?.telegram_id
            ?? sessionStorage.getItem(_SS_KEY_ID)
            ?? new URLSearchParams(location.search).get('telegram_id')
            ?? null;
    }

    /**
     * navigate(page) — Go to another webapp page keeping the telegram_id
     * in the URL so the target page can also call init() successfully.
     */
    function navigate(page) {
        const tid = getTelegramId();
        const sep = page.includes('?') ? '&' : '?';
        location.href = tid ? `${page}${sep}telegram_id=${tid}` : page;
    }

    /**
     * notify(message) — Send a Telegram message to the user's chat.
     * Fire-and-forget (non-blocking, errors are silently logged).
     */
    async function notify(message) {
        const tid = getTelegramId();
        if (!tid) return;
        try {
            await fetch(_BASE + '/api/notify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ telegram_id: parseInt(tid), message, token: _token }),
            });
        } catch (e) {
            console.warn('[DastyorAI] notify failed:', e);
        }
    }

    /**
     * stats() — Fetch per-user usage stats from the server.
     */
    async function stats() {
        const tid = getTelegramId();
        if (!tid) return null;
        try {
            const params = new URLSearchParams({ telegram_id: tid });
            if (_token) params.set('token', _token);
            const r = await fetch(`${_BASE}/api/stats?${params}`);
            return r.ok ? r.json() : null;
        } catch (_) { return null; }
    }

    /**
     * Helper: build a FormData with telegram_id automatically injected.
     * Use this for all /api/ocr_direct, /api/pdf_direct uploads.
     */
    function buildFormData(extraFields = {}) {
        const fd = new FormData();
        const tid = getTelegramId();
        if (tid) fd.append('telegram_id', tid);
        for (const [k, v] of Object.entries(extraFields)) {
            fd.append(k, v);
        }
        return fd;
    }

    /**
     * translate(text, direction) — POST /api/translate.
     * Returns translated string or throws.
     */
    async function translate(text, direction) {
        const r = await _fetch('/api/translate', {
            method: 'POST',
            body: JSON.stringify({ text, direction }),
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || 'Tarjima xatosi');
        return data.translated_text;
    }

    /**
     * translit(text, direction) — POST /api/translit.
     * direction: 'krill_to_lotin' | 'lotin_to_krill'
     * Returns converted string or throws.
     */
    async function translit(text, direction) {
        const r = await _fetch('/api/translit', {
            method: 'POST',
            body: JSON.stringify({ text, direction }),
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || 'Translitatsiya xatosi');
        return data.result;
    }

    /**
     * haptic(type) — Telegram haptic feedback if available.
     * type: 'light' | 'medium' | 'heavy' | 'success' | 'error' | 'warning'
     */
    function haptic(type = 'light') {
        if (!_tg?.HapticFeedback) return;
        if (['light', 'medium', 'heavy'].includes(type)) {
            _tg.HapticFeedback.impactOccurred(type);
        } else {
            _tg.HapticFeedback.notificationOccurred(type);
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    // THEME SYSTEM
    // ═══════════════════════════════════════════════════════════════════

    /**
     * applyTheme() — Reads localStorage('theme') and applies it to the
     * document, Telegram header, and any .da-theme-toggle switches on page.
     * Called automatically by Theme.set() and by init().
     */
    function applyTheme() {
        const dark = localStorage.getItem('theme') !== 'light';
        const root = document.documentElement;

        // Apply class (drives all CSS token overrides in theme.css)
        root.classList.toggle('dark', dark);

        // Sync Telegram WebApp chrome colour
        const headerColor = dark ? '#000000' : '#f5f5f7';
        _tg?.setHeaderColor?.(headerColor);
        _tg?.setBackgroundColor?.(headerColor);

        // Sync any .da-theme-toggle switch elements on the page
        document.querySelectorAll('.da-theme-toggle').forEach(sw => {
            sw.classList.toggle('active', dark);
            sw.setAttribute('aria-checked', String(dark));
        });

        // Dispatch event so individual pages can react
        window.dispatchEvent(new CustomEvent('theme:change', { detail: { dark } }));
        return dark;
    }

    /** Toggle between dark and light, persist, apply. */
    function toggleTheme() {
        const nowDark = localStorage.getItem('theme') !== 'light';
        localStorage.setItem('theme', nowDark ? 'light' : 'dark');
        applyTheme();
        haptic('medium');
    }

    /** Set theme explicitly: setTheme('dark') | setTheme('light') */
    function setTheme(mode) {
        localStorage.setItem('theme', mode === 'dark' ? 'dark' : 'light');
        applyTheme();
    }

    /** Returns true if dark mode is currently active. */
    function isDark() {
        return localStorage.getItem('theme') !== 'light';
    }

    // ═══════════════════════════════════════════════════════════════════
    // i18n BRIDGE  (delegates to I18n if it is loaded)
    // ═══════════════════════════════════════════════════════════════════

    /** Change language and re-render all data-i18n elements. */
    function setLang(lang) {
        if (window.I18n) window.I18n.setLang(lang);
        else localStorage.setItem('lang', lang);
    }

    /** Current language code. */
    function getLang() {
        return window.I18n?.getLang() ?? localStorage.getItem('lang') ?? 'uz_lat';
    }

    /** Shorthand for I18n.t() — translate a key. */
    function t(key) {
        return window.I18n?.t(key) ?? key;
    }

    // ═══════════════════════════════════════════════════════════════════
    // PAGE BOOTSTRAP HELPER
    // ═══════════════════════════════════════════════════════════════════

    /**
     * initUI(options) — Convenience function to set up the full page in one call.
     *
     * options: {
     *   onUser(user) — called with user object after auth,
     *   showLangPicker — show language picker if first visit (default: true),
     *   autoNavLinks — wire all internal <a> through navigate() (default: true),
     *   profileEl — { avatar, name, initials } element IDs to auto-populate
     * }
     *
     * Returns: Promise<user | null>
     */
    async function initUI(options = {}) {
        const {
            onUser         = null,
            showLangPicker = true,
            autoNavLinks   = true,
            profileEl      = {},
        } = options;

        // 1. Apply theme immediately (synchronous — no flicker)
        applyTheme();

        // 2. Apply translations
        if (window.I18n) {
            I18n.apply();
            if (showLangPicker) I18n.showPicker();
        }

        // 3. Wire internal navigation links
        if (autoNavLinks) {
            document.querySelectorAll('a[href]').forEach(a => {
                const href = a.getAttribute('href');
                if (href && !href.startsWith('http') && !href.startsWith('//') && !href.startsWith('#')) {
                    // Remove any previous listener to avoid duplicates
                    a._daNavHandler && a.removeEventListener('click', a._daNavHandler);
                    a._daNavHandler = e => { e.preventDefault(); navigate(href); };
                    a.addEventListener('click', a._daNavHandler);
                }
            });
        }

        // 4. Wire any .da-theme-toggle buttons on the page
        document.querySelectorAll('.da-theme-toggle').forEach(sw => {
            sw.addEventListener('click', toggleTheme);
        });

        // 5. Wire any .da-lang-btn buttons (open picker)
        document.querySelectorAll('.da-lang-btn').forEach(btn => {
            btn.addEventListener('click', () => window.I18n?.showPicker(true));
        });

        // 6. Authenticate and populate profile
        const user = await init();
        if (!user) return null;

        // Auto-fill profile elements if provided
        const { avatarId, nameId, initialsId } = profileEl;
        if (nameId) {
            const el = document.getElementById(nameId);
            if (el) el.textContent = user.first_name || 'User';
        }
        if (initialsId) {
            const el = document.getElementById(initialsId);
            if (el && user.first_name) el.textContent = user.first_name.charAt(0).toUpperCase();
        }
        if (avatarId && user.photo_url) {
            const el = document.getElementById(avatarId);
            if (el) el.innerHTML = `<img src="${user.photo_url}" class="w-full h-full object-cover" referrerpolicy="no-referrer">`;
        }

        if (onUser) onUser(user);
        return user;
    }

    // Dev shortcut: Shift+T toggles theme
    if (typeof document !== 'undefined') {
        document.addEventListener('keydown', e => {
            if (e.shiftKey && e.key === 'T') { toggleTheme(); }
        });
    }

    /**
     * generateDoc(endpoint, payload) — POST to a document generation endpoint,
     * trigger a browser download, and return the Blob.
     * Automatically injects telegram_id and token into the payload.
     *
     * endpoint: '/api/generate_cv' | '/api/generate_obyektivka'
     * payload: plain object with form fields
     * filename: suggested download filename (e.g. 'MyCV.docx')
     */
    async function generateDoc(endpoint, payload, filename) {
        const tid = getTelegramId();
        const enriched = {
            ...payload,
            telegram_id: tid ? parseInt(tid) : null,
            token: _token || undefined,
        };

        const resp = await fetch(_BASE + endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(enriched),
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `Server xatosi (${resp.status})`);
        }

        const blob = await resp.blob();

        // Auto-trigger browser download
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename || 'document.docx';
        document.body.appendChild(a);
        a.click();
        setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 2000);

        return blob;
    }

    // ── Public surface ───────────────────────────────────────────────────

    return {
        // Identity / Auth
        init,
        initUI,
        getUser,
        getToken,
        getTelegramId,
        navigate,
        notify,
        stats,
        buildFormData,
        // Services
        translate,
        translit,
        generateDoc,
        haptic,

        // Theme
        applyTheme,
        toggleTheme,
        setTheme,
        isDark,
        // i18n
        setLang,
        getLang,
        t,
        get tg()   { return _tg; },
        get BASE() { return _BASE; },
    };
})();

