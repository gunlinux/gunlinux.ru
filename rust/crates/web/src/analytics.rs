//! Server-side visit analytics middleware.
//!
//! Records one row per full-page HTML load: the normalized referrer host
//! (the "source" — where the visitor came from), the landing path, and a
//! salted SHA-256 hash of the client IP (raw IPs are never stored; the
//! `SECRET_KEY` salt makes the hash useless without the key, so unique
//! visitor counts work without keeping PII).
//!
//! Deliberately conservative about what counts as a view:
//! - GET only, and only requests that accept `text/html` (a real browser
//!   page load — excludes curl, scripts, feeds);
//! - htmx fragment swaps are excluded (`HX-Request`) — the referrer is only
//!   meaningful for the entry navigation, and counting both would double up
//!   every click;
//! - `/static`, `/admin` and machine endpoints are never tracked.
//!
//! Tracking is best-effort: a failed insert is logged and never fails the
//! request.

use std::net::SocketAddr;

use axum::extract::{ConnectInfo, Request, State};
use axum::http::{header, HeaderMap, Method};
use axum::middleware::Next;
use axum::response::Response;
use chrono::Utc;
use sha2::{Digest, Sha256};

use crate::app::AppState;
use crate::routes::path_query;
use domain::Visit;

/// Middleware: record the visit, then pass the request on. Runs before the
/// response cache, so cache hits are counted exactly once per load.
pub async fn track_visit(State(state): State<AppState>, req: Request, next: Next) -> Response {
    let visit = extract_visit(&state, &req);
    if let Some(visit) = visit {
        if let Err(e) = state.visits.record(&visit).await {
            tracing::warn!("failed to record visit: {e}");
        }
    }
    next.run(req).await
}

/// Build the `Visit` to record for this request, or `None` when it is not a
/// trackable page view.
fn extract_visit(state: &AppState, req: &Request) -> Option<Visit> {
    if !should_track(req) {
        return None;
    }
    let ip_hash = client_ip(req).map(|ip| hash_ip(&ip, state.settings.secret_key.as_bytes()));
    Some(Visit {
        id: None,
        visited_at: Utc::now(),
        referrer: normalize_referrer(req.headers()),
        path: path_query(req.uri()),
        ip_hash,
    })
}

/// Is this request a full-page HTML load worth counting?
fn should_track(req: &Request) -> bool {
    if req.method() != Method::GET {
        return false;
    }
    // htmx fragment swaps are navigations inside the site, not entries.
    if req
        .headers()
        .contains_key(header::HeaderName::from_static("hx-request"))
    {
        return false;
    }
    let accept = req
        .headers()
        .get(header::ACCEPT)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");
    if !accept.contains("text/html") {
        return false;
    }
    let path = req.uri().path();
    if path == "/" {
        return true;
    }
    if path.starts_with("/static")
        || path.starts_with("/admin")
        || path.starts_with("/hx/")
        || matches!(path, "/sitemap.xml" | "/rss.xml" | "/robots.txt" | "/md/")
    {
        return false;
    }
    true
}

/// Normalize the `Referer` header to the bare source host
/// (`https://www.example.com/foo` → `example.com`). Missing/malformed
/// referrers become `None` (a direct visit).
fn normalize_referrer(headers: &HeaderMap) -> Option<String> {
    let raw = headers
        .get(header::REFERER)
        .and_then(|v| v.to_str().ok())?
        .trim();
    if raw.is_empty() {
        return None;
    }
    // Only http(s) URLs carry a meaningful web source.
    let rest = raw
        .strip_prefix("https://")
        .or_else(|| raw.strip_prefix("http://"))?;
    let host = rest.split(['/', ':', '?']).next().unwrap_or(rest).trim();
    let host = host.strip_prefix("www.").unwrap_or(host);
    if host.is_empty() {
        None
    } else {
        Some(host.to_lowercase())
    }
}

/// The client IP: first entry of `X-Forwarded-For` (set by the nginx reverse
/// proxy), falling back to the direct connection address when available.
fn client_ip(req: &Request) -> Option<String> {
    if let Some(xff) = req
        .headers()
        .get("x-forwarded-for")
        .and_then(|v| v.to_str().ok())
    {
        if let Some(first) = xff
            .split(',')
            .next()
            .map(str::trim)
            .filter(|s| !s.is_empty())
        {
            return Some(first.to_string());
        }
    }
    req.extensions()
        .get::<ConnectInfo<SocketAddr>>()
        .map(|ci| ci.0.ip().to_string())
}

/// `sha256(ip || secret)` hex — the salted hash stored instead of the raw IP.
fn hash_ip(ip: &str, secret: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(ip.as_bytes());
    hasher.update(secret);
    hex::encode(hasher.finalize())
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::extract::Request;

    fn req(path: &str) -> Request {
        Request::builder()
            .uri(path)
            .header(header::ACCEPT, "text/html,application/xhtml+xml")
            .body(Body::empty())
            .unwrap()
    }

    #[test]
    fn tracks_html_page_requests_only() {
        assert!(should_track(&req("/")));
        assert!(should_track(&req("/some-post")));
        assert!(should_track(&req("/posts")));
        assert!(should_track(&req("/tags/rust")));
        assert!(!should_track(&req("/static/dist/css/bundle.css")));
        assert!(!should_track(&req("/admin")));
        assert!(!should_track(&req("/hx/icons")));
        assert!(!should_track(&req("/sitemap.xml")));
        assert!(!should_track(&req("/rss.xml")));
        assert!(!should_track(&req("/robots.txt")));
    }

    #[test]
    fn excludes_non_browser_requests() {
        let req = Request::builder()
            .uri("/")
            .header(header::ACCEPT, "*/*")
            .body(Body::empty())
            .unwrap();
        assert!(!should_track(&req));

        let req = Request::builder()
            .uri("/")
            .header(header::ACCEPT, "text/html")
            .header("hx-request", "true")
            .body(Body::empty())
            .unwrap();
        assert!(!should_track(&req));

        let req = Request::builder()
            .method(Method::POST)
            .uri("/")
            .header(header::ACCEPT, "text/html")
            .body(Body::empty())
            .unwrap();
        assert!(!should_track(&req));
    }

    #[test]
    fn normalizes_referrer_to_host() {
        let mut headers = HeaderMap::new();
        headers.insert(
            header::REFERER,
            "https://www.example.com/foo?q=1".parse().unwrap(),
        );
        assert_eq!(normalize_referrer(&headers).as_deref(), Some("example.com"));

        headers.insert(header::REFERER, "http://t.me/s/channel".parse().unwrap());
        assert_eq!(normalize_referrer(&headers).as_deref(), Some("t.me"));

        // Direct visit: no Referer header.
        assert_eq!(normalize_referrer(&HeaderMap::new()), None);

        // Non-http referrers (app schemes) are treated as direct.
        headers.insert(
            header::REFERER,
            "android-app://com.example".parse().unwrap(),
        );
        assert_eq!(normalize_referrer(&headers), None);
    }
}
