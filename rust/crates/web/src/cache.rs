//! Response cache — port of fastapi-cache2's `InMemoryBackend` with a 50s TTL
//! and the `"blog"` namespace (see `app/core/cache.py`).
//!
//! Key builders mirror the Python side:
//! - htmx-aware routes use `{namespace}:{url}:{hx_request_value}` (the `htmx_key_builder`);
//! - static-key routes (`/robots.txt`, `/rss.xml`) use `{namespace}:{url}:`.
//!
//! Namespace invalidation clears the whole cache (only one namespace exists).
//! The `server` binary is a single process, so the moka cache is shared across
//! all request threads and admin writes invalidate it reliably.

use std::time::Duration;

use axum::body::Bytes;
use axum::http::{header, HeaderMap, StatusCode};
use axum::response::{IntoResponse, Response};
use moka::future::Cache as MokaCache;

/// The namespace used for the public response cache (matches fastapi-cache2's
/// `@cache(namespace="blog", ...)` decorators).
pub const NAMESPACE: &str = "blog";
/// Response TTL in seconds (matches `expire=50`).
pub const TTL_SECS: u64 = 50;

/// A serializable cache entry: everything needed to rebuild the HTTP response.
#[derive(Debug, Clone)]
pub struct CachedResponse {
    pub status: StatusCode,
    pub body: Bytes,
    pub content_type: String,
}

impl CachedResponse {
    pub fn into_response(self) -> Response {
        let mut resp = (self.status, self.body).into_response();
        resp.headers_mut()
            .insert(header::CONTENT_TYPE, self.content_type.parse().unwrap());
        resp
    }
}

/// The moka-backed response cache.
#[derive(Clone)]
pub struct Cache {
    inner: MokaCache<String, CachedResponse>,
}

impl Default for Cache {
    fn default() -> Self {
        Self::new()
    }
}

impl Cache {
    pub fn new() -> Self {
        Self {
            inner: MokaCache::builder()
                .time_to_live(Duration::from_secs(TTL_SECS))
                .build(),
        }
    }

    pub async fn get(&self, key: &str) -> Option<CachedResponse> {
        self.inner.get(key).await
    }

    pub async fn insert(&self, key: String, value: CachedResponse) {
        self.inner.insert(key, value).await;
    }

    /// Invalidate every entry in the given namespace. Only the `"blog"`
    /// namespace exists, so this clears the entire cache.
    pub fn clear_namespace(&self, _namespace: &str) {
        self.inner.invalidate_all();
    }
}

/// Build the cache key for htmx-aware routes:
/// `blog:{url}:{HX-Request header value}` (mirrors `htmx_key_builder`).
pub fn htmx_key_builder(uri: &str, headers: &HeaderMap) -> String {
    let hx = headers
        .get(header::HeaderName::from_static("hx-request"))
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");
    format!("{NAMESPACE}:{uri}:{hx}")
}

/// Build the cache key for routes cached with a static key
/// (`/robots.txt`, `/rss.xml`): `blog:{url}:`.
pub fn static_key_builder(uri: &str) -> String {
    format!("{NAMESPACE}:{uri}:")
}
