/**
 * Obyektivka preview + test PDF botga yuborish (@bot watermark).
 */
(function (global) {
  'use strict';

  var previewDebounceTimer = null;
  var previewAbort = null;
  var previewRequestId = 0;
  var _previewImgSrc = '';
  var _previewImgOut = '';
  var _previewImgPromise = null;
  var _testDownloadBusy = false;

  function getApiBase() {
    try {
      if (global.DastyorAI && global.DastyorAI.BASE) return String(global.DastyorAI.BASE).replace(/\/$/, '');
    } catch (_) {}
    var meta = document.querySelector('meta[name="dastyor-api-base"]');
    if (meta && meta.content) return String(meta.content).replace(/\/$/, '');
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
    var payload = buildPreviewRequest();
    if (!payload) return null;
    try {
      if (payload.photo_data) {
        payload.photo_data = await compressPreviewPhoto(payload.photo_data);
      }
    } catch (_) {}
    return payload;
  }

  var previewBlobUrl = '';

  function applyPreviewPdfToIframe(blob, reqId) {
    var iframe = document.getElementById('oby-preview-frame');
    if (!iframe) return;
    if (previewBlobUrl) {
      try { URL.revokeObjectURL(previewBlobUrl); } catch (_) {}
      previewBlobUrl = '';
    }
    previewBlobUrl = URL.createObjectURL(blob);
    function layoutOnce() {
      if (reqId != null && reqId !== previewRequestId) return;
      try { applyPreviewScale(); } catch (_) {}
    }
    iframe.removeAttribute('srcdoc');
    iframe.src = previewBlobUrl;
    iframe.onload = function () {
      layoutOnce();
      setTimeout(layoutOnce, 100);
      setTimeout(layoutOnce, 350);
    };
    requestAnimationFrame(function () { requestAnimationFrame(layoutOnce); });
  }

  var A4_WIDTH_PX = 794;
  var A4_HEIGHT_PX = 2246;

  function readIframeDocSize(iframe) {
    return { width: A4_WIDTH_PX, height: A4_HEIGHT_PX };
  }

  function resizePreviewIframe() {
    var iframe = document.getElementById('oby-preview-frame');
    if (!iframe) return;
    var size = readIframeDocSize(iframe);
    iframe.style.width = Math.ceil(size.width) + 'px';
    iframe.style.height = Math.ceil(size.height) + 'px';
    iframe.style.minHeight = Math.ceil(size.height) + 'px';
  }

  function applyPreviewScale() {
    var pane = document.getElementById('obyPreviewPane');
    var wrap = document.getElementById('obyPreviewScaleWrapper');
    var iframe = document.getElementById('oby-preview-frame');
    var scroll = document.querySelector('.preview-scroll');
    if (!pane || !wrap || !iframe) return;

    resizePreviewIframe();
    var size = readIframeDocSize(iframe);
    var docWidth = size.width;
    var docHeight = size.height;

    var paneWidth = scroll
      ? Math.max(0, scroll.clientWidth - 28)
      : Math.max(0, pane.clientWidth - 8);
    if (!paneWidth) paneWidth = global.innerWidth - 48;

    var scale = Math.min(paneWidth / docWidth, 1);

    var scaledW = Math.ceil(docWidth * scale);
    var scaledH = Math.ceil(docHeight * scale);

    wrap.style.width = scaledW + 'px';
    wrap.style.height = scaledH + 'px';
    wrap.style.margin = '0 auto';
    wrap.style.transform = 'none';

    iframe.style.width = Math.ceil(docWidth) + 'px';
    iframe.style.height = Math.ceil(docHeight) + 'px';
    iframe.style.transform = 'scale(' + scale + ')';
    iframe.style.transformOrigin = 'top left';
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
    if (!payload) return;

    var base = getApiBase();
    var skel = document.getElementById('previewSkeleton');
    if (skel) skel.classList.remove('hidden');
    try {
      var res = await fetch(base + '/api/preview_obyektivka', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: previewAbort ? previewAbort.signal : undefined,
      });
      if (!res.ok || reqId !== previewRequestId) return;
      var blob = await res.blob();
      if (!blob || blob.size < 100) return;
      applyPreviewPdfToIframe(blob, reqId);
    } catch (e) {
      if (e && e.name === 'AbortError') return;
      if (reqId !== previewRequestId) return;
      try {
        if (global.DastyorAI && global.DastyorAI.showToast) {
          global.DastyorAI.showToast('Preview yuklanmadi. Qayta urinib ko\'ring.', 'error');
        }
      } catch (_) {}
    } finally {
      if (skel) skel.classList.add('hidden');
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
      if (typeof global.getDastyorSessionToken === 'function') return global.getDastyorSessionToken();
    } catch (_) {}
    return '';
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
      var payload = await preparePayload();
      if (!payload) throw new Error('Ma\'lumot topilmadi');

      var tid = resolveTgId();
      if (!tid) throw new Error('Foydalanuvchi aniqlanmadi. Botdan qayta oching.');

      payload.telegram_id = parseInt(tid, 10);
      payload.send_to_bot = true;
      var tok = resolveSessionToken();
      if (tok) payload.token = tok;

      var base = getApiBase();
      var res = await fetch(base + '/api/test_obyektivka_pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        var err = '';
        try { err = await res.text(); } catch (_) {}
        throw new Error(err || ('Server ' + res.status));
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
      showToast('Test yuklash xato: ' + msg.slice(0, 180), 'error');
    } finally {
      _testDownloadBusy = false;
      if (btn) {
        btn.disabled = false;
        btn.textContent = 'Test yuklash';
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

  document.addEventListener('DOMContentLoaded', bindPreviewControls);
})(window);
