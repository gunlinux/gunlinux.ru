//! Response cache with two backends: Redis when a `REDIS_URL` is configured,
//! in-memory moka otherwise (the site stays up if Redis is down — connect
//! failures fall back with a warning).
//!
//! Keys are content-versioned: `blog:v{version}:{uri}:{hx}` where `version`
//! is `MAX(COALESCE(update_date, createdon, publishedon))` over the posts
//! table (see `PostRepository::latest_update`). A new post or an edited post
//! bumps the version and orphans every previously cached key, so cached pages
//! are content-fresh the moment the DB changes — the TTL is only a safety net
//! that bounds how long orphaned versions linger.
//!
//! Namespace invalidation (admin writes) clears every version: deletes, tags,
//! icons and categories are not visible to the post version query.

use std::time::Duration;

use axum::body::Bytes;
use axum::http::{header, HeaderMap, StatusCode};
use axum::response::{IntoResponse, Response};
use chrono::{DateTime, Utc};
use moka::future::Cache as MokaCache;
use redis::aio::ConnectionManager;
use serde::{Deserialize, Serialize};

/// The namespace used for the public response cache (matches fastapi-cache2's
/// `@cache(namespace="blog", ...)` decorators).
pub const NAMESPACE: &str = "blog";
/// Safety-net TTL in seconds. Freshness comes from the content version in the
/// key, not the TTL; this only bounds how long orphaned versions linger.
pub const TTL_SECS: u64 = 600;

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

/// Wire format for Redis (`StatusCode`/`Bytes` are not serde-friendly).
#[derive(Debug, Serialize, Deserialize)]
struct WireEntry {
    status: u16,
    body: Vec<u8>,
    content_type: String,
}

impl From<&CachedResponse> for WireEntry {
    fn from(c: &CachedResponse) -> Self {
        Self {
            status: c.status.as_u16(),
            body: c.body.to_vec(),
            content_type: c.content_type.clone(),
        }
    }
}

impl TryFrom<WireEntry> for CachedResponse {
    type Error = ();

    fn try_from(w: WireEntry) -> Result<Self, ()> {
        let status = StatusCode::from_u16(w.status).map_err(|_| ())?;
        Ok(Self {
            status,
            body: Bytes::from(w.body),
            content_type: w.content_type,
        })
    }
}

/// The two cache backends, plus the disabled (no-cache) mode.
#[derive(Clone)]
enum Inner {
    Memory(MokaCache<String, CachedResponse>),
    Redis(ConnectionManager),
    Disabled,
}

/// The response cache: Redis when configured, in-memory moka otherwise.
#[derive(Clone)]
pub struct Cache {
    inner: Inner,
}

impl Default for Cache {
    fn default() -> Self {
        Self::memory()
    }
}

impl Cache {
    /// In-memory backend (used by tests, and as the fallback when no Redis is
    /// configured or reachable).
    pub fn memory() -> Self {
        Self {
            inner: Inner::Memory(
                MokaCache::builder()
                    .time_to_live(Duration::from_secs(TTL_SECS))
                    .max_capacity(4096)
                    .build(),
            ),
        }
    }

    /// No-op backend: every request is a full render, nothing is stored.
    /// Used to benchmark the cache's value (`CACHE_DISABLED=1`).
    pub fn disabled() -> Self {
        Self {
            inner: Inner::Disabled,
        }
    }

    /// Redis backend when `url` is `Some`; `None` or a failed connection
    /// falls back to the in-memory cache (with a warning) so the site stays
    /// up even if Redis is down.
    pub async fn connect(url: Option<&str>) -> Self {
        let Some(url) = url else {
            tracing::debug!("no REDIS_URL configured; using in-memory response cache");
            return Self::memory();
        };
        let client = match redis::Client::open(url) {
            Ok(client) => client,
            Err(e) => {
                tracing::warn!("invalid REDIS_URL ({url}): {e}; using in-memory response cache");
                return Self::memory();
            }
        };
        match ConnectionManager::new(client).await {
            Ok(conn) => {
                tracing::info!("response cache backend: redis ({url})");
                Self {
                    inner: Inner::Redis(conn),
                }
            }
            Err(e) => {
                tracing::warn!(
                    "cannot connect to redis ({url}): {e}; using in-memory response cache"
                );
                Self::memory()
            }
        }
    }

    pub async fn get(&self, key: &str) -> Option<CachedResponse> {
        match &self.inner {
            Inner::Memory(c) => c.get(key).await,
            Inner::Redis(conn) => {
                let mut conn = conn.clone();
                let raw: Option<String> = redis::AsyncCommands::get(&mut conn, key).await.ok()?;
                let wire: WireEntry = serde_json::from_str(&raw?).ok()?;
                wire.try_into().ok()
            }
            Inner::Disabled => None,
        }
    }

    pub async fn insert(&self, key: String, value: CachedResponse) {
        match &self.inner {
            Inner::Memory(c) => c.insert(key, value).await,
            Inner::Redis(conn) => {
                let Ok(json) = serde_json::to_string(&WireEntry::from(&value)) else {
                    return;
                };
                let mut conn = conn.clone();
                let _: Result<(), _> =
                    redis::AsyncCommands::set_ex(&mut conn, key, json, TTL_SECS).await;
            }
            Inner::Disabled => {}
        }
    }

    /// Invalidate every entry in the namespace (all content versions).
    pub async fn clear_namespace(&self, namespace: &str) {
        match &self.inner {
            Inner::Memory(c) => c.invalidate_all(),
            Inner::Redis(conn) => {
                let pattern = format!("{namespace}:*");
                let mut conn = conn.clone();
                // Drop the iterator (which borrows `conn`) before DEL.
                let keys: Vec<String> = {
                    let mut iter: redis::AsyncIter<String> =
                        match redis::AsyncCommands::scan_match(&mut conn, pattern).await {
                            Ok(it) => it,
                            Err(e) => {
                                tracing::warn!("redis scan failed: {e}");
                                return;
                            }
                        };
                    let mut keys = Vec::new();
                    while let Some(key) = iter.next_item().await {
                        keys.push(key);
                    }
                    keys
                };
                if !keys.is_empty() {
                    let _: Result<(), _> = redis::AsyncCommands::del(&mut conn, keys).await;
                }
            }
            Inner::Disabled => {}
        }
    }
}

/// `v{millis}` for a timestamp, `v0` when there are no posts — the version
/// component of every cache key.
pub fn version_component(version: Option<DateTime<Utc>>) -> String {
    match version {
        Some(v) => format!("v{}", v.timestamp_millis()),
        None => "v0".to_string(),
    }
}

/// Build the cache key for htmx-aware routes:
/// `blog:v{version}:{url}:{HX-Request header value}`.
pub fn htmx_key_builder(uri: &str, headers: &HeaderMap, version: Option<DateTime<Utc>>) -> String {
    let hx = headers
        .get(header::HeaderName::from_static("hx-request"))
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");
    format!("{NAMESPACE}:{}:{uri}:{hx}", version_component(version))
}

/// Build the cache key for routes cached with a static key
/// (`/robots.txt`, `/rss.xml`): `blog:v{version}:{url}:`.
pub fn static_key_builder(uri: &str, version: Option<DateTime<Utc>>) -> String {
    format!("{NAMESPACE}:{}:{uri}:", version_component(version))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn version_component_formats_millis() {
        let t = DateTime::parse_from_rfc3339("2026-08-25T12:00:00.123Z")
            .unwrap()
            .with_timezone(&Utc);
        assert_eq!(version_component(Some(t)), "v1787659200123");
        assert_eq!(version_component(None), "v0");
    }

    #[test]
    fn htmx_key_builder_includes_version_and_hx() {
        let t = DateTime::parse_from_rfc3339("2026-08-25T12:00:00.123Z")
            .unwrap()
            .with_timezone(&Utc);
        let mut headers = HeaderMap::new();
        headers.insert(
            header::HeaderName::from_static("hx-request"),
            "true".parse().unwrap(),
        );
        assert_eq!(
            htmx_key_builder("/posts", &headers, Some(t)),
            "blog:v1787659200123:/posts:true"
        );
        assert_eq!(
            htmx_key_builder("/posts", &HeaderMap::new(), Some(t)),
            "blog:v1787659200123:/posts:"
        );
        assert_eq!(static_key_builder("/rss.xml", None), "blog:v0:/rss.xml:");
    }

    /// Round-trip through whatever backend `REDIS_URL` points at. Skips (and
    /// never touches Redis) when the variable is unset — CI without Redis.
    #[tokio::test]
    async fn redis_roundtrip_when_configured() {
        let _ = dotenvy::dotenv();
        let Ok(url) = std::env::var("REDIS_URL") else {
            return;
        };
        let cache = Cache::connect(Some(&url)).await;
        let key = format!("{NAMESPACE}:test:{}", Utc::now().timestamp_millis());
        let entry = CachedResponse {
            status: StatusCode::OK,
            body: Bytes::from_static(b"<html>hi</html>"),
            content_type: "text/html; charset=utf-8".to_string(),
        };
        cache.insert(key.clone(), entry.clone()).await;
        let hit = cache
            .get(&key)
            .await
            .expect("entry should be readable back");
        assert_eq!(hit.status, entry.status);
        assert_eq!(hit.body, entry.body);
        assert_eq!(hit.content_type, entry.content_type);
        cache.clear_namespace(NAMESPACE).await;
        assert!(
            cache.get(&key).await.is_none(),
            "clear_namespace must evict the entry"
        );
    }

    #[tokio::test]
    async fn disabled_backend_never_caches() {
        let cache = Cache::disabled();
        let key = format!("{NAMESPACE}:test:{}", Utc::now().timestamp_millis());
        let entry = CachedResponse {
            status: StatusCode::OK,
            body: Bytes::from_static(b"<html>hi</html>"),
            content_type: "text/html; charset=utf-8".to_string(),
        };
        cache.insert(key.clone(), entry).await;
        assert!(
            cache.get(&key).await.is_none(),
            "disabled cache must never serve"
        );
        cache.clear_namespace(NAMESPACE).await; // must be a no-op, not panic
    }
}
