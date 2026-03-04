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

    /* ── 1. Read persisted preference ────────────────────────────────── */
    // Check storage key, fall back to legacy key used by older app versions
    var stored = localStorage.getItem('da_theme') || localStorage.getItem('theme');

    /* ── 2. Resolve effective theme ──────────────────────────────────── */
    // Strategy: explicit pref > OS media query > default dark
    var prefersDark = (typeof window.matchMedia === 'function')
        && window.matchMedia('(prefers-color-scheme: dark)').matches;

    var isDark;
    if (stored === 'light') {
        isDark = false;
    } else if (stored === 'dark') {
        isDark = true;
    } else {
        // No stored preference → respect OS, else default to dark (app default)
        isDark = prefersDark !== false; // true = dark
    }

    /* ── 3. Apply to <html> IMMEDIATELY (no RAF, no DOMContentLoaded) ── */
    var html = document.documentElement;
    if (isDark) {
        html.classList.add('dark');
        html.classList.remove('light');
    } else {
        html.classList.remove('dark');
        html.classList.add('light');
    }

    /* ── 4. Persist canonical key ────────────────────────────────────── */
    localStorage.setItem('da_theme', isDark ? 'dark' : 'light');
    // Keep legacy key in sync for older pages that still read 'theme'
    localStorage.setItem('theme', isDark ? 'dark' : 'light');

    /* ── 5. Sync Telegram Mini App header color ──────────────────────── */
    // Called both here (best-effort before SDK ready) and after SDK ready
    function syncTelegramColors() {
        var tg = window.Telegram && window.Telegram.WebApp;
        if (!tg) return;
        if (isDark) {
            if (tg.setHeaderColor)     tg.setHeaderColor('#000000');
            if (tg.setBackgroundColor) tg.setBackgroundColor('#000000');
        } else {
            if (tg.setHeaderColor)     tg.setHeaderColor('#f5f5f7');
            if (tg.setBackgroundColor) tg.setBackgroundColor('#f5f5f7');
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

        /** Set theme explicitly: 'dark' | 'light' */
        set: function(theme) {
            var dark = theme === 'dark';
            document.documentElement.classList.toggle('dark', dark);
            document.documentElement.classList.toggle('light', !dark);
            localStorage.setItem('da_theme', dark ? 'dark' : 'light');
            localStorage.setItem('theme', dark ? 'dark' : 'light');
            syncTelegramColors();
            // Notify all listeners
            window.dispatchEvent(new CustomEvent('da-theme-change', { detail: { dark: dark } }));
        },

        /** Toggle between dark and light */
        toggle: function() {
            window.DA_THEME.set(window.DA_THEME.isDark() ? 'light' : 'dark');
        },
    };

})();
