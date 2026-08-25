(function () {
  'use strict';

  // --- Markdown editor (post content textarea) ---
  // Wired to the app's POST /md/ endpoint, which returns python-markdown-
  // compatible HTML (the same contract the Python-era admin used).
  function initEditor() {
    var ta = document.getElementById('content');
    if (!ta || typeof EasyMDE === 'undefined') return;
    new EasyMDE({
      element: ta,
      autosave: { enabled: false },
      spellChecker: false,
      previewRender: function (plainText, preview) {
        fetch('/md/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: 'data=' + encodeURIComponent(plainText),
        })
          .then(function (r) { return r.json(); })
          .then(function (d) { preview.innerHTML = d.data; })
          .catch(function () {
            preview.innerHTML = '<p class="admin-alert admin-alert--error">Preview failed</p>';
          });
        return 'Loading…';
      },
    });
  }

  // --- datetime-local fields ---
  // The server stores UTC (RFC3339); convert the stored value to the
  // browser's local zone for editing. The submitted naive value is parsed
  // back as UTC, exactly as before.
  function initDateTimeFields() {
    var inputs = document.querySelectorAll('input[type="datetime-local"]');
    Array.prototype.forEach.call(inputs, function (input) {
      var m = String(input.value).match(
        /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?(?:Z|[+-]\d{2}:?\d{2})?$/
      );
      if (!m) return;
      var d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0)));
      if (isNaN(d.getTime())) return;
      var pad = function (n) { return (n < 10 ? '0' : '') + n; };
      input.value =
        pad(d.getFullYear()) + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) +
        'T' + pad(d.getHours()) + ':' + pad(d.getMinutes());
    });
  }

  // --- Tag chips ---
  // Checkboxes named `tag_check` are pure UI; the hidden comma-joined `tags`
  // input carries the real value so the form stays a single HashMap on the
  // server.
  function initTagChips() {
    var chipWraps = document.querySelectorAll('.admin-chips');
    Array.prototype.forEach.call(chipWraps, function (wrap) {
      var boxes = wrap.querySelectorAll('input[data-tag]');
      var hidden = wrap.parentNode.querySelector('input[name="tags"]');
      if (!hidden) return;
      var sync = function () {
        var ids = [];
        Array.prototype.forEach.call(boxes, function (box) {
          if (box.checked) ids.push(box.value);
        });
        hidden.value = ids.join(',');
      };
      Array.prototype.forEach.call(boxes, function (box) {
        box.addEventListener('change', sync);
      });
      sync();
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    initEditor();
    initDateTimeFields();
    initTagChips();
  });
})();
