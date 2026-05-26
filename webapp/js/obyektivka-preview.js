/**
 * Obyektivka server-side document preview — same HTML/CSS as PDF export.
 * Watermark + PII masking enabled for unpaid live preview.
 */
(function (global) {
  'use strict';

  var previewDebounceTimer = null;
  var previewAbort = null;
  var previewRequestId = 0;
  var previewZoom = 1;
  var _previewImgSrc = '';
  var _previewImgOut = '';
  var _previewImgPromise = null;

  function getApiBase() {
    try {
      if (global.DastyorAI && global.DastyorAI.BASE) return String(global.DastyorAI.BASE).replace(/\/$/, '');
    } catch (_) {}
    var meta = document.querySelector('meta[name="dastyor-api-base"]');
    if (meta && meta.content) return String(meta.content).replace(/\/$/, '');
    return '';
  }

  function buildPreviewRequest(watermark, maskPii) {
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
      watermark: watermark !== false,
      mask_pii: maskPii !== false,
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

  function applyPreviewHtmlToIframe(html, reqId) {
    var iframe = document.getElementById('oby-preview-frame');
    if (!iframe) return;
    function layoutOnce() {
      if (reqId != null && reqId !== previewRequestId) return;
      try { resizePreviewIframe(); } catch (_) {}
      try { applyPreviewScale(); } catch (_) {}
    }
    iframe.srcdoc = html;
    iframe.onload = layoutOnce;
    requestAnimationFrame(function () { requestAnimationFrame(layoutOnce); });
  }

  function resizePreviewIframe() {
    var iframe = document.getElementById('oby-preview-frame');
    if (!iframe) return;
    try {
      var doc = iframe.contentDocument || iframe.contentWindow.document;
      if (!doc || !doc.body) return;
      var h = Math.max(doc.body.scrollHeight, doc.documentElement.scrollHeight, 297 * 3.78);
      iframe.style.height = Math.ceil(h) + 'px';
    } catch (_) {
      iframe.style.minHeight = '297mm';
    }
  }

  function applyPreviewScale() {
    var pane = document.getElementById('obyPreviewPane');
    var wrap = document.getElementById('obyPreviewScaleWrapper');
    var iframe = document.getElementById('oby-preview-frame');
    if (!pane || !wrap || !iframe) return;

    var paneWidth = Math.max(0, pane.clientWidth - 32);
    var docWidth = Math.max(1, iframe.offsetWidth || 794);
    var fitScale = Math.min(paneWidth / docWidth, 1);
    var scale = fitScale * previewZoom;
    wrap.style.transform = 'scale(' + scale + ')';
    var h = Math.max(1, iframe.offsetHeight || wrap.scrollHeight);
    wrap.style.height = Math.ceil(h * scale) + 'px';
  }

  function setPreviewZoom(value) {
    previewZoom = Math.max(0.45, Math.min(1.6, Number(value) || 1));
    var label = document.getElementById('obyZoomLabel');
    if (label) label.textContent = Math.round(previewZoom * 100) + '%';
    applyPreviewScale();
  }

  async function fetchServerPreview(opts) {
    var immediate = !!(opts && opts.immediate);
    clearTimeout(previewDebounceTimer);
    if (!immediate) {
      previewDebounceTimer = setTimeout(function () {
        fetchServerPreview({ immediate: true });
      }, 420);
      return;
    }

    if (previewAbort) {
      try { previewAbort.abort(); } catch (_) {}
    }
    previewAbort = typeof AbortController !== 'undefined' ? new AbortController() : null;
    var reqId = ++previewRequestId;
    var payload = buildPreviewRequest(true, true);
    if (!payload) return;

    try {
      if (payload.photo_data) {
        payload.photo_data = await compressPreviewPhoto(payload.photo_data);
      }
    } catch (_) {}

    var base = getApiBase();
    try {
      var res = await fetch(base + '/api/preview_obyektivka', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: previewAbort ? previewAbort.signal : undefined,
      });
      if (!res.ok || reqId !== previewRequestId) return;
      var html = await res.text();
      applyPreviewHtmlToIframe(html, reqId);
    } catch (e) {
      if (e && e.name === 'AbortError') return;
    }
  }

  function bindPreviewControls() {
    var zoomIn = document.getElementById('obyZoomIn');
    var zoomOut = document.getElementById('obyZoomOut');
    var zoomReset = document.getElementById('obyZoomReset');
    if (zoomIn) zoomIn.addEventListener('click', function () { setPreviewZoom(previewZoom + 0.1); });
    if (zoomOut) zoomOut.addEventListener('click', function () { setPreviewZoom(previewZoom - 0.1); });
    if (zoomReset) zoomReset.addEventListener('click', function () { setPreviewZoom(1); });
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

  document.addEventListener('DOMContentLoaded', bindPreviewControls);
})(window);
