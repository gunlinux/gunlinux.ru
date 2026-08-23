#!/usr/bin/env python3
"""Side-by-side HTTP parity checker for gunlinux.ru (Python vs Rust).

Runs the route matrix from plan.md §1 against both apps and compares
status code + normalized body per route. Bodies are written to
`<out>/<n>_<route>.{py,rs}.{raw,norm}` for investigation.

Usage:
    python3 compare.py <python_base_url> <rust_base_url> [out_dir]

Stdlib only — no dependency on the project venv.
"""

import re
import sys
import urllib.error
import urllib.parse
import urllib.request

PY_URL = sys.argv[1]
RS_URL = sys.argv[2]
OUT = sys.argv[3] if len(sys.argv) > 3 else "tmp/out"


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Never follow redirects — we want to compare the raw 3xx statuses."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(NoRedirectHandler)


def fetch(base, method, path, data=None):
    req = urllib.request.Request(base + path, method=method, data=data)
    try:
        resp = OPENER.open(req, timeout=30)
        return resp.status, dict(resp.headers), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", errors="replace")


def strip_channel_dates(text):
    """RSS channel pubDate/lastBuildDate come from `datetime.now()` and are
    inherently run-specific. Per-item pubDates come from seeded data and must
    still be compared, so only the channel header (before the first <item>)
    is normalized."""
    head, sep, rest = text.partition("<item>")
    head = re.sub(
        r"(<pubDate>|<lastBuildDate>)[^<]*(</pubDate>|</lastBuildDate>)",
        r"\1\2",
        head,
    )
    return head + sep + rest


def normalize(text, kind):
    """Primary comparison body: strip dynamic parts, collapse whitespace."""
    if kind == "rss":
        text = strip_channel_dates(text)
    if kind == "text":
        return text
    return re.sub(r"\s+", " ", text).strip()


def normalize_raw(text, kind):
    """Secondary comparison body: only dynamic parts removed (no whitespace
    collapsing) so whitespace-sensitive drift (e.g. <pre><code> blocks) is
    not hidden."""
    if kind == "rss":
        return strip_channel_dates(text)
    return text


MD_PAYLOAD = (
    "## Заголовок\n\n"
    "Текст с `inline code` и **bold**.\n\n"
    "```rust\nfn main() { println!(\"hi & bye\"); }\n```\n\n"
    "<div>raw</div>\n\n"
    "- one\n- two\n\n"
    "[link](https://example.com/?a=1&b=2)"
)

# (method, path, data, kind, note)
ROUTES = [
    ("GET", "/", None, "html", ""),
    ("GET", "/posts", None, "html", ""),
    ("GET", "/hx/pages", None, "html", ""),
    ("GET", "/hx/icons", None, "html", ""),
    ("GET", "/robots.txt", None, "text", ""),
    ("GET", "/sitemap.xml", None, "xml", ""),
    ("GET", "/rss.xml", None, "rss", "channel dates stripped"),
    ("POST", "/md/", urllib.parse.urlencode({"data": MD_PAYLOAD}).encode(), "json", ""),
    ("GET", "/tags", None, "html", ""),
    ("GET", "/tags/rust", None, "html", ""),
    ("GET", "/hello-world", None, "html", "seeded post, fenced code + raw HTML"),
    ("GET", "/about-page", None, "html", "page post; pagetitle contains & -> autoescape check"),
    ("GET", "/draft-post", None, "html", "seeded draft -> expect 404"),
    ("GET", "/admin", None, "html", "expect 302 -> /admin/login"),
    ("GET", "/admin/", None, "html", "sqladmin index path (trailing slash)"),
    ("GET", "/admin/login", None, "html", "public login page"),
    ("GET", "/static/dist/css/bundle.css", None, "css", ""),
    ("GET", "/nonexistent-xyz", None, "html", "expect 404"),
    ("GET", "/tags/nonexistent-xyz", None, "html", "expect 404"),
]


def sanitize(path):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", path).strip("_") or "root"


def main():
    rows = []
    for idx, (method, path, data, kind, note) in enumerate(ROUTES, start=1):
        st_py, hd_py, body_py = fetch(PY_URL, method, path, data)
        st_rs, hd_rs, body_rs = fetch(RS_URL, method, path, data)

        norm_py, norm_rs = normalize(body_py, kind), normalize(body_rs, kind)
        raw_py, raw_rs = normalize_raw(body_py, kind), normalize_raw(body_rs, kind)

        status_ok = st_py == st_rs
        norm_ok = norm_py == norm_rs
        raw_ok = raw_py == raw_rs

        base = f"{OUT}/{idx:02d}_{sanitize(path)}"
        with open(f"{base}.py.raw", "w", encoding="utf-8") as f:
            f.write(body_py)
        with open(f"{base}.rs.raw", "w", encoding="utf-8") as f:
            f.write(body_rs)
        with open(f"{base}.py.norm", "w", encoding="utf-8") as f:
            f.write(norm_py)
        with open(f"{base}.rs.norm", "w", encoding="utf-8") as f:
            f.write(norm_rs)
        with open(f"{base}.py.headers", "w", encoding="utf-8") as f:
            f.write("\n".join(f"{k}: {v}" for k, v in hd_py.items()))
        with open(f"{base}.rs.headers", "w", encoding="utf-8") as f:
            f.write("\n".join(f"{k}: {v}" for k, v in hd_rs.items()))

        loc = ""
        # dict(headers) lowercases keys; HTTP header names are case-insensitive.
        loc_py = hd_py.get("Location") or hd_py.get("location")
        loc_rs = hd_rs.get("Location") or hd_rs.get("location")
        if loc_py or loc_rs:
            loc = f"  loc py={loc_py!r} rs={loc_rs!r}"

        rows.append(
            {
                "route": f"{method} {path}",
                "status_py": st_py,
                "status_rs": st_rs,
                "status_ok": status_ok,
                "norm_ok": norm_ok,
                "raw_ok": raw_ok,
                "note": note,
                "loc": loc,
            }
        )

    # Print the table.
    print(f"{'ROUTE':<34} {'PY':>3} {'RS':>3}  {'STATUS':<7} {'BODY(norm)':<10} {'BODY(raw)':<10} NOTE")
    print("-" * 110)
    for r in rows:
        print(
            f"{r['route']:<34} {r['status_py']:>3} {r['status_rs']:>3}  "
            f"{'MATCH' if r['status_ok'] else 'DIFF':<7} "
            f"{'MATCH' if r['norm_ok'] else 'DIFF':<10} "
            f"{'MATCH' if r['raw_ok'] else 'DIFF':<10} {r['note']}{r['loc']}"
        )
    print("-" * 110)

    n_status = sum(not r["status_ok"] for r in rows)
    n_norm = sum(not r["norm_ok"] for r in rows)
    n_raw = sum(not r["raw_ok"] for r in rows)
    print(f"SUMMARY: {len(rows)} routes | status DIFFs: {n_status} | body DIFFs (normalized): {n_norm} | body DIFFs (raw): {n_raw}")

    with open(f"{OUT}/summary.txt", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(
                f"{r['route']}\tpy={r['status_py']}\trs={r['status_rs']}\t"
                f"status={'MATCH' if r['status_ok'] else 'DIFF'}\t"
                f"norm={'MATCH' if r['norm_ok'] else 'DIFF'}\t"
                f"raw={'MATCH' if r['raw_ok'] else 'DIFF'}\t{r['note']}{r['loc']}\n"
            )


if __name__ == "__main__":
    main()
