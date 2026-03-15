/**
 * DASTYOR AI — Universal Theme Initializer  (webapp/theme-init.js)
 * ──────────────────────────────────────────────────────────────────
 * CRITICAL: Load this as the FIRST <script> in <head> — BEFORE any
 * CSS or other scripts. It runs synchronously and sets class="dark"
 * on <html> before the browser paints, eliminating flash-of-wrong-theme.
 *
 * Usage (every page):
 *   <script src="theme-init.js"></script>   ← line 1 in <head>
 *   <link rel="stylesheet" href="theme.css">
 *
 * The theme system writes to localStorage['da_theme'] = 'dark'|'light'.
 * It also syncs the Telegram Mini App header color automatically.
 */
(function() {
    'use strict';

    /* ── 1. Read persisted preference (single source: da_theme, then da_settings_v1, then theme) ── */
    var stored = (localStorage.getItem('da_theme') || localStorage.getItem('theme') || '').toLowerCase();
    if (!stored) {
        try {
            var raw = localStorage.getItem('da_settings_v1');
            if (raw) {
                var s = JSON.parse(raw);
                if (s && s.theme) stored = String(s.theme).toLowerCase();
            }
        } catch (e) {}
    }

    /* ── 2. Resolve effective theme ──────────────────────────────────── */
    var isDark = stored === 'dark' || (stored !== 'light' && stored !== '');
    if (!stored) isDark = true; /* default dark to avoid harsh white */

    /* ── 3. Apply to <html> IMMEDIATELY (no RAF, no DOMContentLoaded) ── */
    var html = document.documentElement;
    if (isDark) {
        html.classList.add('dark');
        html.classList.remove('light');
    } else {
        html.classList.remove('dark');
        html.classList.add('light');
    }

    /* ── 4. Persist canonical keys + da_settings_v1 (barcha sahifalarda bir xil) ─────── */
    var themeVal = isDark ? 'dark' : 'light';
    localStorage.setItem('da_theme', themeVal);
    localStorage.setItem('theme', themeVal);
    try {
        var raw = localStorage.getItem('da_settings_v1');
        var cur = raw ? JSON.parse(raw) : {};
        cur.theme = themeVal;
        localStorage.setItem('da_settings_v1', JSON.stringify(cur));
    } catch (e) {}

    /* ── 5. Sync Telegram Mini App header color ──────────────────────── */
    // Called both here (best-effort before SDK ready) and after SDK ready
    function syncTelegramColors() {
        var tg = window.Telegram && window.Telegram.WebApp;
        if (!tg) return;
        var dark = document.documentElement.classList.contains('dark');
        if (dark) {
            if (tg.setHeaderColor)     tg.setHeaderColor('#121212');
            if (tg.setBackgroundColor) tg.setBackgroundColor('#121212');
        } else {
            if (tg.setHeaderColor)     tg.setHeaderColor('#e5e5e7');
            if (tg.setBackgroundColor) tg.setBackgroundColor('#e5e5e7');
        }
    }
    syncTelegramColors();

    /* ── 6. Re-sync after DOMContentLoaded (SDK may not be ready yet) ── */
    document.addEventListener('DOMContentLoaded', syncTelegramColors);

    /* ── 7. Listen for OS-level theme changes (e.g. auto-dark at sunset) */
    if (typeof window.matchMedia === 'function') {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
            // Only auto-switch if user hasn't set an explicit preference
            if (!localStorage.getItem('da_theme')) {
                var nowDark = e.matches;
                document.documentElement.classList.toggle('dark', nowDark);
                document.documentElement.classList.toggle('light', !nowDark);
                syncTelegramColors();
            }
        });
    }

    /* ── 8. Expose public API on window.DA_THEME ────────────────────── */
    // This is the SINGLE SOURCE OF TRUTH for all pages.
    // app.js toggleTheme() calls this; each page's toggle calls this.
    window.DA_THEME = {
        /** Returns true if current theme is dark */
        isDark: function() {
            return document.documentElement.classList.contains('dark');
        },

        /** Returns 'dark' | 'light' */
        current: function() {
            return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
        },

        /** Set theme explicitly: 'dark' | 'light' — saqlash barcha sahifalarda ishlashi uchun da_settings_v1 ga yozamiz */
        set: function(theme) {
            var dark = theme === 'dark';
            var themeVal = dark ? 'dark' : 'light';
            document.documentElement.classList.toggle('dark', dark);
            document.documentElement.classList.toggle('light', !dark);
            localStorage.setItem('da_theme', themeVal);
            localStorage.setItem('theme', themeVal);
            try {
                var raw = localStorage.getItem('da_settings_v1');
                var cur = raw ? JSON.parse(raw) : {};
                cur.theme = themeVal;
                localStorage.setItem('da_settings_v1', JSON.stringify(cur));
            } catch (e) {}
            syncTelegramColors();
            window.dispatchEvent(new CustomEvent('da-theme-change', { detail: { dark: dark } }));
        },

        /** Toggle between dark and light */
        toggle: function() {
            window.DA_THEME.set(window.DA_THEME.isDark() ? 'light' : 'dark');
        },
    };

})();
