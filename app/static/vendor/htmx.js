// mini-htmx — a minimal, dependency-free reimplementation of the subset of
// htmx 2.0.8 (https://htmx.org) used by gunlinux.ru. htmx is released under
// the Zero-Clause BSD license; this file is a derivative work trimmed to
// exactly the behaviors the site's templates rely on:
//
//   hx-get + hx-trigger ("load" | "click", the only triggers used)
//   hx-target (plain CSS selectors)
//   hx-swap (innerHTML; unknown values such as the site's "posts" fall back
//            to innerHTML exactly as htmx does; "none" skips the swap)
//   hx-push-url (true pushes the request URL; a literal value is pushed
//                verbatim — the logo fetches /posts but pushes "/")
//   back/forward history restore from an in-memory snapshot cache (htmx
//                style); URLs without a snapshot fall back to a full load
//   scroll-to-top on click-triggered swaps (load-triggered swaps skip it —
//                they only fill in the initial render)
//   htmx:afterSwap event, fired on the swap target (bubbles)
//   HX-Request / HX-Current-URL request headers — the server keys its
//   dual-mode rendering (full page vs fragment) off HX-Request
//
// Everything else — forms, hx-boost, out-of-band swaps, indicators,
// morphdom, SSE/WS, extensions, the htmx.* JS API — is intentionally absent.
//
// Known deviations from stock htmx:
//   * History restore is a session-only in-memory snapshot of
//     `.page__content` (htmx caches whole pages across sessions); a URL with
//     no snapshot — e.g. an admin page, whose htmx swaps target `#list-table`
//     — performs a full page load on back/forward.
//   * hx-trigger modifiers (once/delay/throttle/...), non-load/click triggers,
//     extended hx-target selectors (closest/find/next/...), and the
//     htmx.ajax() API are not supported.
//
// Regenerate the minified build with:
//   npx esbuild app/static/vendor/htmx.js --minify \
//     --outfile=app/static/vendor/htmx.min.js

(function () {
  'use strict'

  var htmx = {
    config: { defaultSwapStyle: 'innerHTML' },
    version: 'mini-2.0.8',
  }

  function getAttr(elt, name) {
    return elt.getAttribute(name)
  }

  function closestWithAttr(elt, name) {
    for (var node = elt; node && node.nodeType === 1; node = node.parentElement) {
      if (node.hasAttribute(name)) return node
    }
    return null
  }

  function requestHeaders() {
    return {
      'HX-Request': 'true',
      'HX-Current-URL': window.location.href,
    }
  }

  // The site only ever uses bare "load" and "click" triggers. htmx's default
  // trigger for hx-get on a non-form element is click, so a missing
  // hx-trigger means the same.
  function parseTriggers(value) {
    if (!value) return ['click']
    var names = []
    value.split(',').forEach(function (part) {
      var name = part.trim().split(/\s+/)[0]
      if (name === 'load' || name === 'click') names.push(name)
    })
    return names.length ? names : ['click']
  }

  function resolveTarget(elt, selector) {
    if (!selector) return elt
    return document.querySelector(selector) || elt
  }

  function dispatchAfterSwap(target, elt, path) {
    target.dispatchEvent(new CustomEvent('htmx:afterSwap', {
      bubbles: true,
      detail: { elt: elt, target: target, path: path, isError: false },
    }))
  }

  // History restore. Click navigations push a URL via hx-push-url; pressing
  // back/forward then only fires `popstate` (no reload), so the page must
  // restore itself. Save a snapshot of `.page__content` per URL (htmx-style,
  // minus the network round-trip). A URL without a snapshot means the entry
  // was never htmx-navigated to this session (e.g. an admin page — its swaps
  // target `#list-table`, not `.page__content`): a full page load is the
  // correct restore then.
  var HISTORY_CACHE_SIZE = 20
  var historyCache = {}

  function isMainTarget(elt) {
    return elt.classList && elt.classList.contains('page__content')
  }

  function saveSnapshot(url, target) {
    historyCache[url] = {
      html: target.innerHTML,
      title: document.title,
      scrollY: window.scrollY,
    }
    var keys = Object.keys(historyCache)
    if (keys.length > HISTORY_CACHE_SIZE) delete historyCache[keys[0]]
  }

  function restoreSnapshot(url) {
    var snap = historyCache[url]
    if (!snap) return false
    var target = document.querySelector('.page__content')
    if (!target) return false
    target.innerHTML = snap.html
    document.title = snap.title
    window.scrollTo(0, snap.scrollY)
    return true
  }

  window.addEventListener('popstate', function () {
    if (!restoreSnapshot(window.location.href)) {
      window.location.reload()
    }
  })

  // Fire the request and, on success, swap the fragment into the target.
  function issueRequest(elt) {
    var url = getAttr(elt, 'hx-get')
    if (!url) return

    fetch(url, { headers: requestHeaders() })
      .then(function (resp) {
        if (!resp.ok) throw new Error('HTTP ' + resp.status)
        return resp.text()
      })
      .then(function (content) {
        var target = resolveTarget(elt, getAttr(elt, 'hx-target'))
        var swapStyle = getAttr(elt, 'hx-swap') || htmx.config.defaultSwapStyle
        var pushUrl = getAttr(elt, 'hx-push-url')
        // Only `.page__content` navigations (the public site's pattern) take
        // part in snapshot restore; admin swaps target other elements and
        // fall back to a full page load on back/forward.
        var mainTarget = pushUrl && isMainTarget(target)

        if (mainTarget) {
          // Snapshot the page being left — its URL is still current until
          // pushState below — so Back can restore it verbatim.
          saveSnapshot(window.location.href, target)
        }

        if (pushUrl === 'true') {
          history.pushState({}, '', url)
        } else if (pushUrl) {
          // Literal hx-push-url value (e.g. "/") wins over the request URL,
          // matching stock htmx — the logo fetches /posts but the address
          // bar must read /.
          history.pushState({}, '', pushUrl)
        }

        if (swapStyle === 'none') {
          dispatchAfterSwap(target, elt, url)
          return
        }

        target.innerHTML = content
        // Fire any hx-trigger="load" elements that arrived inside the swap
        // (htmx processes newly-swapped-in content the same way).
        fireLoadRequests(target)
        // Click-triggered swaps navigate to a new page; open it at the top
        // instead of carrying the previous page's scroll position over (the
        // fragment swap otherwise preserves it). Load-triggered swaps only
        // fill in the initial render and must not scroll.
        if (parseTriggers(getAttr(elt, 'hx-trigger')).indexOf('load') === -1) {
          window.scrollTo(0, 0)
        }
        if (mainTarget) {
          // The pushed URL is current now; remember what it renders so
          // Forward restores it too.
          saveSnapshot(window.location.href, target)
        }
        dispatchAfterSwap(target, elt, url)
      })
      .catch(function (err) {
        console.error('mini-htmx: request to ' + url + ' failed', err)
      })
  }

  function fireLoadRequests(root) {
    if (!root.querySelectorAll) return
    var nodes = root.querySelectorAll('[hx-get]')
    for (var i = 0; i < nodes.length; i++) {
      if (parseTriggers(getAttr(nodes[i], 'hx-trigger')).indexOf('load') !== -1) {
        issueRequest(nodes[i])
      }
    }
  }

  document.addEventListener('click', function (evt) {
    // Leave modified clicks (new tab / open-in-window) to the browser.
    if (evt.metaKey || evt.ctrlKey || evt.shiftKey || evt.altKey) return
    if (evt.button !== 0) return
    var elt = closestWithAttr(evt.target, 'hx-get')
    if (!elt) return
    if (elt.tagName === 'A') evt.preventDefault()
    issueRequest(elt)
  })

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      fireLoadRequests(document)
    })
  } else {
    fireLoadRequests(document)
  }

  window.htmx = htmx
})()
