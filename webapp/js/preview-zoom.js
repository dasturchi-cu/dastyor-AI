/**
 * Premium preview zoom slider — CV & Obyektivka.
 * Preview-only; does not affect export output.
 */
(function (global) {
  'use strict';

  var LEVELS = [50, 75, 100, 125, 150, 175, 200];
  var MIN = 50;
  var MAX = 200;
  var DEFAULT = 100;

  function nearestLevel(pct) {
    var best = LEVELS[0];
    var bestDist = Infinity;
    for (var i = 0; i < LEVELS.length; i++) {
      var d = Math.abs(LEVELS[i] - pct);
      if (d < bestDist) {
        bestDist = d;
        best = LEVELS[i];
      }
    }
    return best;
  }

  function pctToPos(pct) {
    return (pct - MIN) / (MAX - MIN);
  }

  function posToPct(pos) {
    return MIN + Math.max(0, Math.min(1, pos)) * (MAX - MIN);
  }

  function touchDistance(t0, t1) {
    var dx = t1.clientX - t0.clientX;
    var dy = t1.clientY - t0.clientY;
    return Math.sqrt(dx * dx + dy * dy);
  }

  function create(options) {
    var mount = options.mount;
    if (typeof mount === 'string') mount = document.querySelector(mount);
    if (!mount) return null;

    var previewEl = options.previewEl;
    if (typeof previewEl === 'string') previewEl = document.querySelector(previewEl);

    var percent = DEFAULT;
    var listeners = [];
    var dragging = false;
    var pinchStartDist = 0;
    var pinchStartPct = DEFAULT;

    mount.classList.add('pz-zoom');
    mount.setAttribute('role', 'group');
    mount.setAttribute('aria-label', 'Preview zoom');
    mount.innerHTML =
      '<span class="pz-zoom-label">50%</span>' +
      '<div class="pz-zoom-track" tabindex="0">' +
        '<div class="pz-zoom-fill"></div>' +
        '<div class="pz-zoom-thumb" role="slider" aria-valuemin="50" aria-valuemax="200" aria-valuenow="100" aria-label="Zoom"></div>' +
      '</div>' +
      '<span class="pz-zoom-label pz-zoom-label--end">200%</span>';

    var track = mount.querySelector('.pz-zoom-track');
    var thumb = mount.querySelector('.pz-zoom-thumb');
    var fill = mount.querySelector('.pz-zoom-fill');

    function updateUI(pct) {
      var pos = pctToPos(pct);
      var leftPct = (pos * 100) + '%';
      thumb.style.left = leftPct;
      fill.style.width = leftPct;
      thumb.setAttribute('aria-valuenow', String(Math.round(pct)));
    }

    function notify() {
      var ratio = percent / 100;
      for (var i = 0; i < listeners.length; i++) {
        try { listeners[i](ratio, percent); } catch (_) {}
      }
    }

    function setPercent(pct, opts) {
      opts = opts || {};
      pct = Math.max(MIN, Math.min(MAX, Number(pct) || DEFAULT));
      if (!opts.dragging) pct = nearestLevel(pct);
      percent = pct;
      updateUI(pct);
      if (!opts.silent) notify();
    }

    function step(delta) {
      var current = nearestLevel(percent);
      var idx = LEVELS.indexOf(current);
      if (idx < 0) idx = LEVELS.indexOf(DEFAULT);
      idx = Math.max(0, Math.min(LEVELS.length - 1, idx + delta));
      setPercent(LEVELS[idx]);
    }

    function posFromEvent(e) {
      var rect = track.getBoundingClientRect();
      if (!rect.width) return 0;
      var clientX = e.clientX;
      if (e.touches && e.touches.length) clientX = e.touches[0].clientX;
      return (clientX - rect.left) / rect.width;
    }

    function beginDrag() {
      dragging = true;
      track.classList.add('is-dragging');
    }

    function endDrag(snap) {
      dragging = false;
      track.classList.remove('is-dragging');
      if (snap) setPercent(percent);
    }

    function onPointerDown(e) {
      if (e.button != null && e.button !== 0) return;
      beginDrag();
      setPercent(posToPct(posFromEvent(e)), { dragging: true });
      e.preventDefault();
    }

    function onPointerMove(e) {
      if (!dragging) return;
      setPercent(posToPct(posFromEvent(e)), { dragging: true, silent: true });
      notify();
      e.preventDefault();
    }

    function onPointerUp() {
      if (!dragging) return;
      endDrag(true);
    }

    track.addEventListener('mousedown', onPointerDown);
    thumb.addEventListener('mousedown', function (e) {
      e.stopPropagation();
      onPointerDown(e);
    });
    global.addEventListener('mousemove', onPointerMove);
    global.addEventListener('mouseup', onPointerUp);

    track.addEventListener('touchstart', function (e) {
      if (e.touches.length !== 1) return;
      beginDrag();
      setPercent(posToPct(posFromEvent(e)), { dragging: true });
    }, { passive: true });

    track.addEventListener('touchmove', function (e) {
      if (!dragging || e.touches.length !== 1) return;
      setPercent(posToPct(posFromEvent(e)), { dragging: true, silent: true });
      notify();
    }, { passive: true });

    track.addEventListener('touchend', function () {
      if (!dragging) return;
      endDrag(true);
    });

    track.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight' || e.key === 'ArrowUp') {
        e.preventDefault();
        step(1);
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') {
        e.preventDefault();
        step(-1);
      } else if (e.key === 'Home') {
        e.preventDefault();
        setPercent(MIN);
      } else if (e.key === 'End') {
        e.preventDefault();
        setPercent(MAX);
      }
    });

    function onWheel(e) {
      var overPreview = previewEl && (previewEl.contains(e.target) || previewEl === e.target);
      var overMount = mount.contains(e.target);
      if (!overPreview && !overMount && !e.ctrlKey && !e.metaKey) return;
      e.preventDefault();
      if (e.deltaY < 0) step(1);
      else if (e.deltaY > 0) step(-1);
    }

    mount.addEventListener('wheel', onWheel, { passive: false });

    if (previewEl) {
      previewEl.addEventListener('wheel', onWheel, { passive: false });

      previewEl.addEventListener('touchstart', function (e) {
        if (e.touches.length === 2) {
          pinchStartDist = touchDistance(e.touches[0], e.touches[1]);
          pinchStartPct = percent;
          beginDrag();
          e.preventDefault();
        }
      }, { passive: false });

      previewEl.addEventListener('touchmove', function (e) {
        if (e.touches.length === 2 && pinchStartDist > 0) {
          var dist = touchDistance(e.touches[0], e.touches[1]);
          var ratio = dist / pinchStartDist;
          setPercent(pinchStartPct * ratio, { dragging: true, silent: true });
          notify();
          e.preventDefault();
        }
      }, { passive: false });

      previewEl.addEventListener('touchend', function (e) {
        if (e.touches.length < 2 && pinchStartDist > 0) {
          pinchStartDist = 0;
          endDrag(true);
        }
      });

      previewEl.addEventListener('touchcancel', function () {
        pinchStartDist = 0;
        endDrag(true);
      });
    }

    setPercent(DEFAULT, { silent: true });
    updateUI(DEFAULT);

    return {
      getMultiplier: function () { return percent / 100; },
      getPercent: function () { return percent; },
      setPercent: setPercent,
      step: step,
      reset: function () { setPercent(DEFAULT); },
      isDragging: function () { return dragging || pinchStartDist > 0; },
      onChange: function (fn) { listeners.push(fn); },
    };
  }

  global.DastyorPreviewZoom = {
    create: create,
    LEVELS: LEVELS,
    DEFAULT: DEFAULT,
    MIN: MIN,
    MAX: MAX,
  };
})(window);
