/**
 * Obyektivka preview + demo PDF botga yuborish (@bot watermark).
 * Jonli ko'rinish: server HTML iframe (CV kabi, tez). PDF faqat demo yuklash uchun.
 */
(function (global) {
  'use strict';

  var previewDebounceTimer = null;
  var previewAbort = null;
  var previewRequestId = 0;
  var _previewMode = 'pdf';
  var _previewImgSrc = '';
  var _previewImgOut = '';
  var _previewImgPromise = null;
  var _testDownloadBusy = false;
  var _iframeBlobUrl = '';
  var zoomCtrl = null;
  var WRAP_TRANSITION = 'width 200ms cubic-bezier(0.4, 0, 0.2, 1), height 200ms cubic-bezier(0.4, 0, 0.2, 1)';
  var PAGE_GAP = 12;
  var FETCH_TIMEOUT_MS = 120000;
  var RENDER_TIMEOUT_MS = preferWorkerlessPdf() ? 90000 : 45000;

  var PDF_JS_URLS = [
    'vendor/pdf.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js',
    'https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.min.js',
  ];
  var PDF_WORKER_URLS = [
    'vendor/pdf.worker.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js',
    'https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.worker.min.js',
  ];

  function webappAssetUrl(rel) {
    try {
      return new URL(String(rel || ''), global.location.href).href;
    } catch (_) {
      return String(rel || '');
    }
  }

  function isTelegramWebView() {
    try {
      return !!(global.Telegram && global.Telegram.WebApp && global.Telegram.WebApp.initData);
    } catch (_) {
      return false;
    }
  }

  function isMobileDevice() {
    try {
      var ua = String((global.navigator && global.navigator.userAgent) || '');
      return /Android|iPhone|iPad|iPod|Mobile|Telegram/i.test(ua);
    } catch (_) {
      return false;
    }
  }

  /** Telegram iOS/Android WebView: PDF worker va iframe ishlamaydi. */
  function preferWorkerlessPdf() {
    return isTelegramWebView() || isMobileDevice();
  }

  function previewRenderScale() {
    return preferWorkerlessPdf() ? 1.0 : 1.5;
  }

  function getApiBase() {
    try {
      if (global.DastyorAI && global.DastyorAI.BASE) return String(global.DastyorAI.BASE).replace(/\/$/, '');
    } catch (_) {}
    try {
      if (typeof global.getApiUrl === 'function') return String(global.getApiUrl()).replace(/\/$/, '');
    } catch (_) {}
    var meta = document.querySelector('meta[name="dastyor-api-base"]');
    if (meta && meta.content) return String(meta.content).replace(/\/$/, '');
    try {
      if (/^https?:\/\//i.test(global.location.origin || '')) {
        return String(global.location.origin).replace(/\/$/, '');
      }
    } catch (_) {}
    return '';
  }

  function buildPreviewRequest() {
    if (typeof global.buildObyPayload !== 'function') return null;
    var p = global.buildObyPayload('pdf');
    return {
      lang: p.lang,
      fullname: p.fullname,
      birthdate: p.bdate || '',
      birthplace: p.bplace || '',
      nation: p.nation || '',
      party: p.party || '',
      education: p.edu || '',
      graduated: p.grad || '',
      specialty: p.spec || '',
      degree: p.deg || '',
      scientific_title: p.ttl || '',
      languages: p.langs || '',
      military_rank: p.mil || '',
      awards: p.award || '',
      departmental_awards: p.idor || '',
      deputy: p.dep || '',
      current_job: p.current_job || '',
      current_job_year: p.current_job_year || '',
      work_experience: (p.works || []).map(function (w) {
        return {
          year: ((w.f || '') + ((w.f || w.t) ? '-' : '') + (w.t || '')).replace(/^-|-$/g, ''),
          position: w.d || '',
        };
      }),
      relatives: (p.rels || []).map(function (r) {
        return {
          degree: r.type || '',
          fullname: r.name || '',
          birth_year_place: r.birth || '',
          work_place: r.job || '',
          address: r.addr || '',
        };
      }),
      photo_data: p.photo_data || '',
      watermark: true,
      mask_pii: false,
    };
  }

  async function compressPreviewPhoto(src) {
    if (!src || String(src).indexOf('data:image') !== 0) return src || '';
    if (src === _previewImgSrc && _previewImgOut) return _previewImgOut;
    if (_previewImgPromise && src === _previewImgSrc) return _previewImgPromise;

    _previewImgSrc = src;
    _previewImgOut = '';
    _previewImgPromise = new Promise(function (resolve) {
      try {
        var img = new Image();
        img.onload = function () {
          try {
            var maxW = 480;
            var scale = Math.min(1, maxW / Math.max(img.width, 1));
            var w = Math.max(1, Math.round(img.width * scale));
            var h = Math.max(1, Math.round(img.height * scale));
            var canvas = document.createElement('canvas');
            canvas.width = w;
            canvas.height = h;
            var ctx = canvas.getContext('2d');
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, w, h);
            ctx.drawImage(img, 0, 0, w, h);
            _previewImgOut = canvas.toDataURL('image/jpeg', 0.88);
          } catch (_) {
            _previewImgOut = src;
          }
          resolve(_previewImgOut);
        };
        img.onerror = function () {
          _previewImgOut = src;
          resolve(_previewImgOut);
        };
        img.src = src;
      } catch (_) {
        _previewImgOut = src;
        resolve(_previewImgOut);
      }
    });
    return _previewImgPromise;
  }

  async function preparePayload() {
    try {
      if (global.DastyorAI && global.DastyorAI.ensureAuth) {
        await global.DastyorAI.ensureAuth();
      }
    } catch (_) {}

    var payload = buildPreviewRequest();
    if (!payload) return null;

    attachWebappAuth(payload);
    var tid = resolveTgId();
    if (tid) payload.telegram_id = parseInt(tid, 10);

    try {
      if (payload.photo_data) {
        payload.photo_data = await compressPreviewPhoto(payload.photo_data);
      }
    } catch (_) {}
    return payload;
  }

  var _pdfJsPromise = null;
  var _pageWidthPx = 794;
  var _pageHeightPx = 1123;

  function isPdfBuffer(buf) {
    if (!buf || buf.byteLength < 4) return false;
    var u8 = new Uint8Array(buf, 0, 4);
    return u8[0] === 0x25 && u8[1] === 0x50 && u8[2] === 0x44 && u8[3] === 0x46;
  }

  async function normalizePdfBuffer(buf) {
    if (isPdfBuffer(buf)) return buf;
    var u8 = new Uint8Array(buf);
    if (u8.length >= 2 && u8[0] === 0x1f && u8[1] === 0x8b && typeof DecompressionStream !== 'undefined') {
      try {
        var out = await new Response(new Blob([u8]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
        if (isPdfBuffer(out)) return out;
      } catch (_) {}
    }
    var head = '';
    try {
      head = String.fromCharCode(u8[0], u8[1], u8[2], u8[3]);
    } catch (_) {}
    if (head === '{' || head === '[{"') {
      try {
        var js = JSON.parse(new TextDecoder().decode(u8));
        throw new Error((js && (js.detail || js.message)) || 'Server JSON xato qaytardi');
      } catch (e) {
        if (e && e.message && e.message.indexOf('Server') === 0) throw e;
      }
    }
    throw new Error('Server PDF emas qaytardi');
  }

  function configurePdfWorker(pdfjs, workerIndex) {
    if (!pdfjs || !pdfjs.GlobalWorkerOptions) return;
    if (preferWorkerlessPdf()) return;
    var idx = workerIndex || 0;
    pdfjs.GlobalWorkerOptions.workerSrc = webappAssetUrl(PDF_WORKER_URLS[idx] || PDF_WORKER_URLS[0]);
  }

  function loadPdfDocument(pdfjs, buf) {
    var workerless = preferWorkerlessPdf();
    var attempts = workerless
      ? [
          { disableWorker: true, disableFontFace: false, useSystemFonts: true },
          { disableWorker: true, disableFontFace: true, useSystemFonts: true },
          { disableWorker: true, useSystemFonts: true, useWorkerFetch: false, isEvalSupported: false },
        ]
      : [
          { disableFontFace: true, useSystemFonts: true },
          { disableWorker: true, disableFontFace: false, useSystemFonts: true },
          { disableWorker: true, disableFontFace: true, useSystemFonts: true },
        ];
    var chain = Promise.reject(new Error('start'));
    attempts.forEach(function (opts) {
      chain = chain.catch(function () {
        return pdfjs.getDocument(Object.assign({ data: buf }, opts)).promise;
      });
    });
    return chain;
  }

  function loadScriptOnce(url) {
    return new Promise(function (resolve, reject) {
      var abs = webappAssetUrl(url);
      var existing = document.querySelector('script[data-oby-pdfjs="' + abs + '"]');
      if (existing) {
        existing.addEventListener('load', function () { resolve(); }, { once: true });
        existing.addEventListener('error', function () { reject(new Error('Script yuklanmadi: ' + abs)); }, { once: true });
        return;
      }
      var s = document.createElement('script');
      s.src = abs;
      s.async = true;
      s.setAttribute('data-oby-pdfjs', abs);
      s.onload = function () { resolve(); };
      s.onerror = function () { reject(new Error('Script yuklanmadi: ' + abs)); };
      document.head.appendChild(s);
    });
  }

  function loadPdfJs() {
    if (global.pdfjsLib) {
      configurePdfWorker(global.pdfjsLib, 0);
      return Promise.resolve(global.pdfjsLib);
    }
    if (_pdfJsPromise) return _pdfJsPromise;

    _pdfJsPromise = (async function () {
      var lastErr = null;
      for (var i = 0; i < PDF_JS_URLS.length; i++) {
        try {
          await loadScriptOnce(PDF_JS_URLS[i]);
          if (!global.pdfjsLib) throw new Error('pdfjsLib topilmadi');
          configurePdfWorker(global.pdfjsLib, i);
          return global.pdfjsLib;
        } catch (err) {
          lastErr = err;
        }
      }
      throw lastErr || new Error('PDF.js yuklanmadi');
    })();

    return _pdfJsPromise;
  }

  function getPreviewHost() {
    return document.getElementById('oby-preview-pdf-host');
  }

  function getPreviewIframe() {
    return document.getElementById('oby-preview-frame');
  }

  function ensurePreviewVisible() {
    try {
      var main = document.getElementById('main-card');
      if (main) main.classList.remove('hidden');
      var lang = document.getElementById('lang-card');
      if (lang) lang.classList.add('hidden');
      var section = document.getElementById('preview-section');
      if (section) section.style.display = 'block';
    } catch (_) {}
  }

  function setPreviewLoading(on) {
    var skel = document.getElementById('previewSkeleton');
    if (!skel) return;
    skel.classList.toggle('hidden', !on);
    skel.setAttribute('aria-hidden', on ? 'false' : 'true');
  }

  function clearPreviewError() {
    var el = document.getElementById('oby-preview-error');
    if (el) {
      el.classList.add('hidden');
      el.textContent = '';
    }
  }

  function formatPreviewError(message) {
    var raw = String(message || 'Noma\'lum xato').trim();
    if (raw.charAt(0) === '{') {
      try {
        var js = JSON.parse(raw);
        var code = js.code || js.status;
        if (code === 502 || code === '502') {
          return 'Server javob bermadi (502). Bir oz kutib qayta urinib ko\'ring.';
        }
        if (js.message) return String(js.message).slice(0, 220);
        if (js.detail) return String(js.detail).slice(0, 220);
      } catch (_) {}
    }
    return raw.slice(0, 220);
  }

  function showPreviewError(message, reqId) {
    if (reqId != null && reqId !== previewRequestId) return;
    var friendly = formatPreviewError(message);
    ensurePreviewVisible();
    clearPreviewError();
    var host = getPreviewHost();
    var iframe = getPreviewIframe();
    if (host) {
      host.innerHTML = '';
      host.style.display = 'none';
    }
    if (iframe) {
      iframe.hidden = true;
      iframe.style.display = 'none';
      iframe.removeAttribute('src');
    }
    var errEl = document.getElementById('oby-preview-error');
    if (!errEl) {
      errEl = document.createElement('div');
      errEl.id = 'oby-preview-error';
      errEl.className = 'oby-preview-error';
      errEl.setAttribute('role', 'alert');
      var port = document.querySelector('.preview-port');
      if (port) port.insertBefore(errEl, port.firstChild);
    }
    errEl.classList.remove('hidden');
    errEl.innerHTML =
      '<div class="oby-preview-error-title">Preview yuklanmadi</div>' +
      '<div class="oby-preview-error-msg">' + friendly.replace(/</g, '&lt;') + '</div>' +
      '<button type="button" class="btn btn-outline btn-sm oby-preview-retry">Qayta urinish</button>';
    var retry = errEl.querySelector('.oby-preview-retry');
    if (retry && !retry.dataset.bound) {
      retry.dataset.bound = '1';
      retry.addEventListener('click', function () {
        clearPreviewError();
        fetchServerPreview({ immediate: true });
      });
    }
    showToast('Preview yuklanmadi: ' + friendly.slice(0, 120), 'error');
  }

  function revokeIframeBlob() {
    if (_iframeBlobUrl) {
      try { URL.revokeObjectURL(_iframeBlobUrl); } catch (_) {}
      _iframeBlobUrl = '';
    }
  }

  function withTimeout(promise, ms, label) {
    return new Promise(function (resolve, reject) {
      var done = false;
      var timer = setTimeout(function () {
        if (done) return;
        done = true;
        reject(new Error((label || 'Amal') + ' vaqti tugadi (' + Math.round(ms / 1000) + 's)'));
      }, ms);
      promise.then(function (v) {
        if (done) return;
        done = true;
        clearTimeout(timer);
        resolve(v);
      }).catch(function (e) {
        if (done) return;
        done = true;
        clearTimeout(timer);
        reject(e);
      });
    });
  }

  function schedulePreviewLayout(reqId) {
    function layoutOnce() {
      if (reqId != null && reqId !== previewRequestId) return;
      try { applyPreviewScale(); } catch (_) {}
    }
    requestAnimationFrame(function () { requestAnimationFrame(layoutOnce); });
    setTimeout(layoutOnce, 60);
    setTimeout(layoutOnce, 220);
    setTimeout(layoutOnce, 500);
  }

  function appendPreviewPage(host, canvas, pw, ph) {
    if (preferWorkerlessPdf()) {
      var img = document.createElement('img');
      img.className = 'oby-preview-page';
      img.dataset.pageWidth = String(pw);
      img.dataset.pageHeight = String(ph);
      img.alt = 'Obyektivka preview';
      img.decoding = 'async';
      img.loading = 'eager';
      try {
        img.src = canvas.toDataURL('image/jpeg', 0.9);
        host.appendChild(img);
        return;
      } catch (_) {}
    }
    canvas.className = 'oby-preview-page';
    canvas.dataset.pageWidth = String(pw);
    canvas.dataset.pageHeight = String(ph);
    host.appendChild(canvas);
  }

  function getHtmlDocSize(iframe) {
    var a4w = Math.round(210 * (96 / 25.4));
    var a4h = Math.round(297 * (96 / 25.4));
    var w = a4w;
    var h = a4h;
    try {
      var doc = iframe.contentDocument || (iframe.contentWindow && iframe.contentWindow.document);
      if (!doc) return { w: w, h: h };
      var root = doc.querySelector('.page') || doc.body;
      var html = doc.documentElement;
      w = Math.max(a4w, root.scrollWidth || 0, root.offsetWidth || 0, html.scrollWidth || 0);
      h = Math.max(a4h, root.scrollHeight || 0, root.offsetHeight || 0, html.scrollHeight || 0);
    } catch (_) {}
    return { w: w, h: h };
  }

  function resizeHtmlPreviewIframe() {
    var iframe = getPreviewIframe();
    if (!iframe || !iframe.contentDocument || !iframe.contentDocument.body) return;
    var size = getHtmlDocSize(iframe);
    iframe.style.width = size.w + 'px';
    iframe.style.height = Math.ceil(size.h) + 'px';
    iframe.style.minHeight = Math.ceil(size.h) + 'px';
  }

  function scaleHtmlPreview() {
    var pane = document.getElementById('obyPreviewPane');
    var iframe = getPreviewIframe();
    var wrap = document.getElementById('obyPreviewScaleWrapper');
    var scroll = document.querySelector('.preview-scroll');
    if (!pane || !iframe || !wrap) return;

    try { resizeHtmlPreviewIframe(); } catch (_) {}

    var paneStyle = pane ? getComputedStyle(pane) : null;
    var paneWidth = pane
      ? Math.max(0, pane.clientWidth - parseFloat((paneStyle && paneStyle.paddingLeft) || '0') - parseFloat((paneStyle && paneStyle.paddingRight) || '0'))
      : Math.max(120, (global.innerWidth || 360) - 48);
    if (scroll && scroll.clientWidth) {
      paneWidth = Math.max(120, scroll.clientWidth - 32);
    }

    var size = getHtmlDocSize(iframe);
    var actualWidth = Math.max(size.w, 320);
    var rawH = Math.max(size.h, 400);
    var fitScale = paneWidth / actualWidth;
    var baseScale = Math.max(0.22, Math.min(fitScale, 1));
    var userMul = zoomCtrl ? zoomCtrl.getMultiplier() : 1;
    var scale = baseScale * userMul;
    var animate = !zoomCtrl || !zoomCtrl.isDragging();
    var scaledW = Math.max(1, Math.ceil(actualWidth * scale));
    var scaledH = Math.max(1, Math.ceil(rawH * scale));

    iframe.style.position = 'absolute';
    iframe.style.left = '50%';
    iframe.style.top = '0';
    iframe.style.width = actualWidth + 'px';
    iframe.style.height = rawH + 'px';
    iframe.style.minHeight = rawH + 'px';
    iframe.style.transform = 'translateX(-50%) scale(' + scale + ')';
    iframe.style.transformOrigin = 'top center';
    iframe.style.transition = animate ? WRAP_TRANSITION : 'none';
    iframe.style.border = '0';
    iframe.style.background = '#fff';

    wrap.style.width = scaledW + 'px';
    wrap.style.maxWidth = '100%';
    wrap.style.height = scaledH + 'px';
    wrap.style.minHeight = scaledH + 'px';
    wrap.style.margin = '0 auto';
    wrap.style.transform = 'none';
    wrap.style.transition = animate ? WRAP_TRANSITION : 'none';
    wrap.style.overflow = 'visible';
    wrap.style.position = 'relative';
  }

  function showHtmlPreview(html, reqId) {
    if (reqId != null && reqId !== previewRequestId) return;
    var host = getPreviewHost();
    var iframe = getPreviewIframe();
    if (!iframe) throw new Error('Preview iframe topilmadi');

    _previewMode = 'html';
    clearPreviewError();
    revokeIframeBlob();
    if (host) {
      host.innerHTML = '';
      host.style.display = 'none';
    }

    iframe.hidden = false;
    iframe.style.display = 'block';
    iframe.removeAttribute('src');
    iframe.srcdoc = html;

    function layoutOnce() {
      if (reqId != null && reqId !== previewRequestId) return;
      try { scaleHtmlPreview(); } catch (_) {}
    }
    iframe.onload = layoutOnce;
    requestAnimationFrame(function () { requestAnimationFrame(layoutOnce); });
    setTimeout(layoutOnce, 80);
    setTimeout(layoutOnce, 280);
    setTimeout(layoutOnce, 600);
  }

  async function fetchHtmlPreview(payload, signal) {
    var base = getApiBase();
    var res = await withTimeout(
      fetch(base + '/api/preview_obyektivka_html', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/html' },
        body: JSON.stringify(payload),
        signal: signal,
      }),
      FETCH_TIMEOUT_MS,
      'HTML preview'
    );
    if (!res.ok) {
      var errBody = '';
      try { errBody = await res.text(); } catch (_) {}
      throw new Error(errBody || ('Server xatosi: ' + res.status));
    }
    var html = await res.text();
    if (!html || html.length < 80) throw new Error('Serverdan bo\'sh HTML keldi');
    return html;
  }

  function showPdfEmbed(blob, reqId) {
    if (reqId != null && reqId !== previewRequestId) return;
    _previewMode = 'pdf';
    var host = getPreviewHost();
    var iframe = getPreviewIframe();
    if (!host) throw new Error('Preview host topilmadi');

    clearPreviewError();
    if (iframe) {
      iframe.hidden = true;
      iframe.style.display = 'none';
      iframe.removeAttribute('src');
    }
    revokeIframeBlob();
    host.innerHTML = '';
    host.style.display = 'block';
    _iframeBlobUrl = URL.createObjectURL(blob);
    var embed = document.createElement('embed');
    embed.type = 'application/pdf';
    embed.src = _iframeBlobUrl + '#toolbar=0&navpanes=0&scrollbar=0';
    embed.className = 'oby-preview-embed';
    embed.style.cssText = 'width:100%;min-height:min(68vh,560px);height:min(68vh,560px);border:0;display:block;background:#fff';
    host.appendChild(embed);
  }

  function showPdfIframe(blob, reqId) {
    if (reqId != null && reqId !== previewRequestId) return;
    _previewMode = 'pdf';
    var host = getPreviewHost();
    var iframe = getPreviewIframe();
    if (!iframe) throw new Error('Preview iframe topilmadi');

    clearPreviewError();
    if (host) {
      host.innerHTML = '';
      host.style.display = 'none';
    }

    revokeIframeBlob();
    _iframeBlobUrl = URL.createObjectURL(blob);
    iframe.hidden = false;
    iframe.style.display = 'block';
    iframe.style.width = '100%';
    iframe.style.minHeight = 'min(68vh, 560px)';
    iframe.style.height = 'min(68vh, 560px)';
    iframe.style.border = '0';
    iframe.style.background = '#fff';
    iframe.setAttribute('src', _iframeBlobUrl);

    return new Promise(function (resolve, reject) {
      var settled = false;
      function finish(ok) {
        if (settled) return;
        settled = true;
        if (ok) resolve();
        else reject(new Error('PDF iframe ochilmadi'));
      }
      iframe.onload = function () { finish(true); };
      iframe.onerror = function () { finish(false); };
      setTimeout(function () {
        try {
          var doc = iframe.contentDocument || (iframe.contentWindow && iframe.contentWindow.document);
          if (doc && doc.body && doc.body.childNodes && doc.body.childNodes.length) finish(true);
          else finish(false);
        } catch (_) {
          finish(false);
        }
      }, 1800);
    });
  }

  async function renderPreviewPdfImages(blob, reqId) {
    var host = getPreviewHost();
    var iframe = getPreviewIframe();
    if (!host) return;

    _previewMode = 'pdf';

    var buf = await blob.arrayBuffer();
    if (reqId != null && reqId !== previewRequestId) return;
    if (!buf || buf.byteLength < 100) {
      throw new Error('Serverdan bo\'sh javob keldi');
    }

    var header = String.fromCharCode(buf[0], buf[1], buf[2], buf[3]);
    if (header !== '%PDF') {
      throw new Error('Server PDF emas qaytardi');
    }

    var pdfjs = await loadPdfJs();
    if (reqId != null && reqId !== previewRequestId) return;

    var pdf = await withTimeout(
      loadPdfDocument(pdfjs, buf),
      RENDER_TIMEOUT_MS,
      'PDF render'
    );
    if (reqId != null && reqId !== previewRequestId) return;

    clearPreviewError();
    if (iframe) {
      iframe.hidden = true;
      iframe.style.display = 'none';
      iframe.removeAttribute('src');
      revokeIframeBlob();
    }

    host.style.display = 'block';
    host.innerHTML = '';
    host.style.transform = 'none';
    host.style.width = 'auto';
    host.style.height = 'auto';

    var renderScale = previewRenderScale();
    var firstPageW = 0;
    var firstPageH = 0;
    var totalH = 0;
    var maxW = 0;
    var rendered = 0;

    for (var pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
      try {
        var page = await pdf.getPage(pageNum);
        if (reqId != null && reqId !== previewRequestId) return;
        var viewport = page.getViewport({ scale: renderScale });
        var pw = Math.floor(viewport.width);
        var ph = Math.floor(viewport.height);

        var canvas = document.createElement('canvas');
        canvas.width = pw;
        canvas.height = ph;
        await page.render({
          canvasContext: canvas.getContext('2d'),
          viewport: viewport,
        }).promise;
        if (reqId != null && reqId !== previewRequestId) return;

        appendPreviewPage(host, canvas, pw, ph);
        rendered += 1;

        if (pageNum === 1) {
          firstPageW = pw;
          firstPageH = ph;
        }
        maxW = Math.max(maxW, pw);
        totalH += ph + (pageNum < pdf.numPages ? PAGE_GAP : 0);
      } catch (pageErr) {
        if (rendered === 0) throw pageErr;
        break;
      }
    }

    if (!rendered) throw new Error('PDF sahifalari chizilmadi');

    host.dataset.docWidth = String(Math.ceil(maxW));
    host.dataset.docHeight = String(Math.ceil(totalH));
    host.dataset.pageWidth = String(firstPageW || Math.ceil(maxW));
    host.dataset.pageHeight = String(firstPageH || Math.ceil(totalH / Math.max(1, pdf.numPages)));
    _pageWidthPx = Number(host.dataset.pageWidth) || 794;
    _pageHeightPx = Number(host.dataset.pageHeight) || 1123;

    if (zoomCtrl && zoomCtrl.reset) zoomCtrl.reset();
    schedulePreviewLayout(reqId);
  }

  async function applyPreviewPdf(blob, reqId) {
    ensurePreviewVisible();
    var errors = [];

    try {
      await renderPreviewPdfImages(blob, reqId);
      return;
    } catch (err) {
      errors.push(err);
    }

    try {
      await showPdfEmbed(blob, reqId);
      schedulePreviewLayout(reqId);
      return;
    } catch (err) {
      errors.push(err);
    }

    try {
      await showPdfIframe(blob, reqId);
      return;
    } catch (err) {
      errors.push(err);
    }

    var msg = errors.map(function (e) { return (e && e.message) || String(e); }).join(' | ');
    throw new Error(msg || 'Preview ochilmadi');
  }

  var A4_WIDTH_PX = 794;
  var A4_HEIGHT_PX = 1123;

  function readPageSize() {
    var host = getPreviewHost();
    if (host) {
      var pw = Number(host.dataset.pageWidth || 0);
      var ph = Number(host.dataset.pageHeight || 0);
      if (pw > 0 && ph > 0) return { width: pw, height: ph };
      var first = host.querySelector('.oby-preview-page');
      if (first) {
        return {
          width: Number(first.dataset.pageWidth || first.naturalWidth || first.width || A4_WIDTH_PX),
          height: Number(first.dataset.pageHeight || first.naturalHeight || first.height || A4_HEIGHT_PX),
        };
      }
    }
    return { width: _pageWidthPx || A4_WIDTH_PX, height: _pageHeightPx || A4_HEIGHT_PX };
  }

  function computeFitPageScale(scroll, pageSize) {
    var padX = 32;
    var padY = 36;
    var paneWidth = scroll
      ? Math.max(120, scroll.clientWidth - padX)
      : Math.max(120, (global.innerWidth || 360) - 48);
    var paneHeight = scroll
      ? Math.max(120, scroll.clientHeight - padY)
      : Math.max(200, Math.min(640, (global.innerHeight || 600) * 0.55));
    if (!paneWidth || !paneHeight) return 1;
    var scaleW = paneWidth / Math.max(1, pageSize.width);
    var scaleH = paneHeight / Math.max(1, pageSize.height);
    return Math.min(scaleW, scaleH, 1.25);
  }

  function applyPreviewScale() {
    if (_previewMode === 'html') {
      scaleHtmlPreview();
      return;
    }

    var wrap = document.getElementById('obyPreviewScaleWrapper');
    var host = getPreviewHost();
    var scroll = document.querySelector('.preview-scroll');
    if (!wrap || !host) return;

    var pages = host.querySelectorAll('.oby-preview-page');
    if (!pages.length) return;

    var pageSize = readPageSize();
    var fitScale = computeFitPageScale(scroll, pageSize);
    var userMul = zoomCtrl ? zoomCtrl.getMultiplier() : 1;
    var scale = fitScale * userMul;
    var animate = !zoomCtrl || !zoomCtrl.isDragging();

    var totalH = 0;
    var maxW = 0;

    for (var i = 0; i < pages.length; i++) {
      var el = pages[i];
      var pw = Number(el.dataset.pageWidth || el.naturalWidth || el.width || pageSize.width);
      var ph = Number(el.dataset.pageHeight || el.naturalHeight || el.height || pageSize.height);
      var w = Math.max(1, Math.round(pw * scale));
      var h = Math.max(1, Math.round(ph * scale));
      el.style.width = w + 'px';
      el.style.height = h + 'px';
      el.style.display = 'block';
      el.style.margin = '0 auto';
      el.style.marginBottom = (i < pages.length - 1) ? PAGE_GAP + 'px' : '0';
      if (el.tagName === 'IMG') {
        el.style.objectFit = 'contain';
      }
      maxW = Math.max(maxW, w);
      totalH += h + (i < pages.length - 1 ? PAGE_GAP : 0);
    }

    wrap.style.width = maxW + 'px';
    wrap.style.height = totalH + 'px';
    wrap.style.minWidth = maxW + 'px';
    wrap.style.minHeight = totalH + 'px';
    wrap.style.margin = '0 auto';
    wrap.style.transform = 'none';
    wrap.style.transition = animate ? WRAP_TRANSITION : 'none';
    wrap.style.overflow = 'visible';

    host.style.width = maxW + 'px';
    host.style.height = totalH + 'px';
    host.style.transform = 'none';
    host.style.transition = 'none';
    host.dataset.docWidth = String(maxW);
    host.dataset.docHeight = String(totalH);
  }

  function initPreviewZoom() {
    if (!global.DastyorPreviewZoom) return;
    var mount = document.getElementById('obyPreviewZoom');
    if (!mount) return;
    zoomCtrl = global.DastyorPreviewZoom.create({
      mount: mount,
      previewEl: document.querySelector('.preview-scroll'),
    });
    if (!zoomCtrl) return;
    zoomCtrl.onChange(function () {
      try { applyPreviewScale(); } catch (_) {}
    });
  }

  function initPreviewResizeObserver() {
    var scroll = document.querySelector('.preview-scroll');
    if (!scroll || typeof ResizeObserver === 'undefined') return;
    var ro = new ResizeObserver(function () {
      try { applyPreviewScale(); } catch (_) {}
    });
    ro.observe(scroll);
    var section = document.getElementById('preview-section');
    if (section) ro.observe(section);
  }

  async function fetchServerPreview(opts) {
    var immediate = !!(opts && opts.immediate);
    clearTimeout(previewDebounceTimer);
    if (!immediate) {
      previewDebounceTimer = setTimeout(function () {
        fetchServerPreview({ immediate: true });
      }, 500);
      return;
    }

    if (previewAbort) {
      try { previewAbort.abort(); } catch (_) {}
    }
    previewAbort = typeof AbortController !== 'undefined' ? new AbortController() : null;
    var reqId = ++previewRequestId;
    var payload = await preparePayload();
    if (!payload) {
      showPreviewError('Forma ma\'lumotlari topilmadi. Tilni tanlang yoki maydonlarni to\'ldiring.', reqId);
      return;
    }

    ensurePreviewVisible();
    clearPreviewError();
    setPreviewLoading(true);

    var base = getApiBase();
    if (!base) {
      setPreviewLoading(false);
      showPreviewError('API manzili aniqlanmadi.', reqId);
      return;
    }

    try {
      var html = await fetchHtmlPreview(payload, previewAbort ? previewAbort.signal : undefined);
      if (reqId !== previewRequestId) return;
      showHtmlPreview(html, reqId);
    } catch (e) {
      if (e && e.name === 'AbortError') return;
      if (reqId !== previewRequestId) return;
      showPreviewError((e && e.message) ? e.message : String(e), reqId);
    } finally {
      if (reqId === previewRequestId) setPreviewLoading(false);
    }
  }

  function resolveTgId() {
    try {
      if (typeof global.resolveTelegramId === 'function') return global.resolveTelegramId();
    } catch (_) {}
    return null;
  }

  function resolveSessionToken() {
    try {
      if (global.DastyorAI && global.DastyorAI.getToken) return global.DastyorAI.getToken() || null;
    } catch (_) {}
    try {
      if (typeof global.getDastyorSessionToken === 'function') return global.getDastyorSessionToken();
    } catch (_) {}
    return '';
  }

  function attachWebappAuth(payload) {
    var authExtras = {};
    try {
      if (global.DastyorAI && global.DastyorAI.getAuthExtras) {
        authExtras = global.DastyorAI.getAuthExtras() || {};
      }
    } catch (_) {}

    var tok = resolveSessionToken() || authExtras.token || null;
    if (tok) payload.token = tok;

    if (authExtras.init_data) {
      payload.init_data = authExtras.init_data;
    } else {
      try {
        var tg = global.Telegram && global.Telegram.WebApp;
        if (tg && tg.initData) payload.init_data = tg.initData;
      } catch (_) {}
    }

    var tid = resolveTgId();
    if (tid && !payload.telegram_id) {
      payload.telegram_id = parseInt(tid, 10);
    }
    return payload;
  }

  async function readApiError(res) {
    if (typeof global.dastyorReadApiError === 'function') {
      try { return await global.dastyorReadApiError(res); } catch (_) {}
    }
    try { return await res.text(); } catch (_) { return ''; }
  }

  function showToast(msg, type) {
    try {
      if (global.DastyorAI && global.DastyorAI.showToast) {
        global.DastyorAI.showToast(msg, type || 'info');
        return;
      }
    } catch (_) {}
    alert(msg);
  }

  async function downloadTestPdf() {
    if (_testDownloadBusy) return;
    var btn = document.getElementById('obyTestDownloadBtn');
    _testDownloadBusy = true;
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Botga yuborilmoqda...';
    }
    try {
      if (global.DastyorAI && global.DastyorAI.ensureAuth) {
        await global.DastyorAI.ensureAuth();
      }
    } catch (_) {}

    try {
      var payload = await preparePayload();
      if (!payload) throw new Error('Ma\'lumot topilmadi');

      var tid = resolveTgId();
      if (!tid) throw new Error('Foydalanuvchi aniqlanmadi. Botdan qayta oching.');

      payload.telegram_id = parseInt(tid, 10);
      payload.send_to_bot = true;
      attachWebappAuth(payload);

      var base = getApiBase();
      var res = await fetch(base + '/api/test_obyektivka_pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        var errMsg = await readApiError(res);
        throw new Error(errMsg || ('Server ' + res.status));
      }

      var js = await res.json();
      if (!js || !js.sent) throw new Error('Telegramga yuborib bo\'lmadi');

      var tg = global.Telegram && global.Telegram.WebApp ? global.Telegram.WebApp : null;
      if (tg && tg.HapticFeedback && tg.HapticFeedback.notificationOccurred) {
        tg.HapticFeedback.notificationOccurred('success');
      }
      showToast('✅ Demo PDF botga yuborildi. Chatda watermark bilan oching.', 'success');
      setTimeout(function () {
        try { if (tg && tg.close) tg.close(); } catch (_) {}
      }, 900);
    } catch (e) {
      var msg = (e && e.message) ? String(e.message) : String(e);
      showToast('Demo yuklash xato: ' + msg.slice(0, 180), 'error');
    } finally {
      _testDownloadBusy = false;
      if (btn) {
        btn.disabled = false;
        btn.textContent = 'Demo yuklash';
      }
    }
  }

  function bindPreviewControls() {
    var testBtn = document.getElementById('obyTestDownloadBtn');
    if (testBtn) testBtn.addEventListener('click', downloadTestPdf);

    window.addEventListener('resize', function () {
      try { applyPreviewScale(); } catch (_) {}
    });
  }

  global.updatePreview = function updatePreview() {
    fetchServerPreview({ immediate: false });
  };

  global.scaleLivePreview = function scaleLivePreview() {
    applyPreviewScale();
  };

  global.triggerObyPreviewNow = function triggerObyPreviewNow() {
    fetchServerPreview({ immediate: true });
  };

  global.downloadTestObyektivka = downloadTestPdf;

  document.addEventListener('DOMContentLoaded', function () {
    if (global.pdfjsLib) configurePdfWorker(global.pdfjsLib, 0);
    initPreviewZoom();
    initPreviewResizeObserver();
    bindPreviewControls();
  });
})(window);
