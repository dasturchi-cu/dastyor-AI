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

    /**
     * applyTheme() — Apply dark/light theme from localStorage and sync
     * with Telegram WebApp header color.
     */
    function applyTheme() {
        const dark = localStorage.getItem('theme') !== 'light';
        if (dark) {
            document.documentElement.classList.add('dark');
            _tg?.setHeaderColor?.('#000000');
            _tg?.setBackgroundColor?.('#000000');
        } else {
            document.documentElement.classList.remove('dark');
            _tg?.setHeaderColor?.('#f5f5f7');
            _tg?.setBackgroundColor?.('#f5f5f7');
        }
        return dark;
    }

    // ── Public surface ───────────────────────────────────────────────────
    return {
        init,
        getUser,
        getToken,
        getTelegramId,
        navigate,
        notify,
        stats,
        buildFormData,
        translate,
        translit,
        haptic,
        applyTheme,
        get tg() { return _tg; },
        get BASE() { return _BASE; },
    };
})();
