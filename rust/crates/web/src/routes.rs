//! Route handlers — a port of `app/api/posts.py` + `app/api/tags.py`.
//!
//! Behavior contract (frozen from the Python app):
//! - cacheable GET routes use the moka response cache (TTL 50s, namespace
//!   `"blog"`); `/sitemap.xml`, `/tags*` and `POST /md/` are NOT cached;
//! - htmx dual-mode: if the `HX-Request` header is present the htmx fragment
//!   template is rendered instead of the full page;
//! - the catch-all `GET /{alias}` returns 404 for missing posts and for
//!   non-published, non-page posts.

use std::collections::HashMap;
use std::future::Future;

use axum::body::Body;
use axum::extract::{Path, State};
use axum::http::{header, HeaderMap, StatusCode, Uri};
use axum::response::{IntoResponse, Response};
use axum::Json;
use chrono::Utc;
use minijinja::context;

use crate::app::AppState;
use crate::cache::{htmx_key_builder, static_key_builder, Cache, CachedResponse};
use crate::services::{IconService, PostService, TagService, WebError};
use crate::templates::{group_posts_by_year, render, PostView};

/// `text/plain` with charset, matching Starlette's charset appending.
const TEXT_PLAIN: &str = "text/plain; charset=utf-8";
const TEXT_HTML: &str = "text/html; charset=utf-8";
const APP_XML: &str = "application/xml";
const APP_RSS: &str = "application/rss+xml";

fn html_response(body: String) -> Response {
    ([(header::CONTENT_TYPE, TEXT_HTML)], body).into_response()
}

fn text_response(body: String, content_type: &str) -> Response {
    ([(header::CONTENT_TYPE, content_type)], body).into_response()
}

pub fn not_found() -> Response {
    StatusCode::NOT_FOUND.into_response()
}

impl IntoResponse for WebError {
    fn into_response(self) -> Response {
        let status = match &self {
            WebError::NotFound => StatusCode::NOT_FOUND,
            WebError::Conflict(_) => StatusCode::CONFLICT,
            WebError::Internal(_) => StatusCode::INTERNAL_SERVER_ERROR,
        };
        (status, self.to_string()).into_response()
    }
}

pub fn path_query(uri: &Uri) -> String {
    uri.path_and_query()
        .map(|pq| pq.as_str().to_string())
        .unwrap_or_else(|| uri.path().to_string())
}

fn is_htmx_request(headers: &HeaderMap) -> bool {
    headers.contains_key(header::HeaderName::from_static("hx-request"))
}

/// Serve a rendered (or otherwise produced) response through the cache:
/// return a hit immediately; otherwise run `f`, cache the 200 response and
/// return it. Non-200 responses are not cached (matches fastapi-cache, which
/// never sees raised exceptions).
async fn with_cache<F, Fut>(cache: &Cache, key: String, f: F) -> Result<Response, WebError>
where
    F: FnOnce() -> Fut,
    Fut: Future<Output = Result<Response, WebError>>,
{
    if let Some(hit) = cache.get(&key).await {
        return Ok(hit.into_response());
    }
    let resp = f().await?;
    if resp.status() != StatusCode::OK {
        return Ok(resp);
    }
    // Extract the pieces before returning (Response is not Clone).
    let status = resp.status();
    let content_type = resp
        .headers()
        .get(header::CONTENT_TYPE)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("text/html")
        .to_string();
    let body = axum::body::to_bytes(resp.into_body(), usize::MAX)
        .await
        .map_err(|e| WebError::Internal(format!("buffer body: {e}")))?;
    let cached = CachedResponse {
        status,
        body: body.clone(),
        content_type: content_type.clone(),
    };
    cache.insert(key, cached).await;
    Ok((status, [(header::CONTENT_TYPE, content_type)], body).into_response())
}

/// `GET /` — index page (cached, htmx-aware key; no htmx variant exists).
pub async fn index(
    State(state): State<AppState>,
    headers: HeaderMap,
    uri: Uri,
) -> Result<Response, WebError> {
    let key = htmx_key_builder(&path_query(&uri), &headers);
    with_cache(&state.cache, key, || async {
        let body = render(&state.templates, "index.html", context! {})?;
        Ok(html_response(body))
    })
    .await
}

/// `GET /posts` — full listing or htmx fragment (cached, htmx-aware key).
pub async fn posts(
    State(state): State<AppState>,
    headers: HeaderMap,
    uri: Uri,
) -> Result<Response, WebError> {
    let key = htmx_key_builder(&path_query(&uri), &headers);
    with_cache(&state.cache, key, || async {
        let post_service = PostService::new(state.posts.clone());
        let all_posts = post_service.get_all_published_content().await?;
        let posts_by_year = group_posts_by_year(all_posts);
        let template = if is_htmx_request(&headers) {
            "posts.htmx"
        } else {
            "posts.html"
        };
        let body = render(
            &state.templates,
            template,
            context! { posts_by_year => posts_by_year },
        )?;
        Ok(html_response(body))
    })
    .await
}

/// `GET /hx/pages` — nav pages fragment (cached, htmx-aware key).
pub async fn pages_hx(
    State(state): State<AppState>,
    headers: HeaderMap,
    uri: Uri,
) -> Result<Response, WebError> {
    let key = htmx_key_builder(&path_query(&uri), &headers);
    with_cache(&state.cache, key, || async {
        let post_service = PostService::new(state.posts.clone());
        let pages = post_service.get_page_posts().await?;
        let body = render(&state.templates, "pages.htmx", context! { pages => pages })?;
        Ok(html_response(body))
    })
    .await
}

/// `GET /hx/icons` — footer icons fragment (cached, htmx-aware key).
pub async fn icons_hx(
    State(state): State<AppState>,
    headers: HeaderMap,
    uri: Uri,
) -> Result<Response, WebError> {
    let key = htmx_key_builder(&path_query(&uri), &headers);
    with_cache(&state.cache, key, || async {
        let icon_service = IconService::new(state.icons.clone());
        let icons = icon_service.get_all_icons().await?;
        let body = render(
            &state.templates,
            "icons/icons.htmx",
            context! { icons => icons },
        )?;
        Ok(html_response(body))
    })
    .await
}

/// `GET /robots.txt` — exact body, cached with a static key.
pub async fn robots(
    State(state): State<AppState>,
    headers: HeaderMap,
    uri: Uri,
) -> Result<Response, WebError> {
    let key = static_key_builder(&path_query(&uri));
    with_cache(&state.cache, key, || async {
        let content =
            "\nUser-agent: *\nCrawl-delay: 2\nDisallow: /tags/*\nHost: gunlinux.ru\n".to_string();
        let _ = &headers;
        Ok(text_response(content, TEXT_PLAIN))
    })
    .await
}

/// `GET /sitemap.xml` — relative `<loc>/alias</loc>` entries for pages then
/// published posts. NOT cached (the Python route has no `@cache` decorator).
pub async fn sitemap(State(state): State<AppState>) -> Result<Response, WebError> {
    let post_service = PostService::new(state.posts.clone());
    let pages = post_service.get_page_posts().await?;
    let posts_list = post_service.get_published_posts().await?;
    let mut xml = String::from("<?xml version=\"1.0\" encoding=\"UTF-8\"?>");
    xml.push_str("<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">");
    for p in pages.iter().chain(posts_list.iter()) {
        xml.push_str(&format!("<url><loc>/{}</loc></url>", p.alias));
    }
    xml.push_str("</urlset>");
    Ok(text_response(xml, APP_XML))
}

/// `GET /rss.xml` — RSS feed from published posts (cached, static key).
pub async fn rss(
    State(state): State<AppState>,
    headers: HeaderMap,
    uri: Uri,
) -> Result<Response, WebError> {
    let key = static_key_builder(&path_query(&uri));
    with_cache(&state.cache, key, || async {
        let post_service = PostService::new(state.posts.clone());
        let posts_list = post_service.get_published_posts().await?;
        let date = Utc::now();
        let _ = &headers;
        let body = render(
            &state.templates,
            "rss.xml",
            context! { posts => posts_list, date => date },
        )?;
        Ok(text_response(body, APP_RSS))
    })
    .await
}

/// `POST /md/` — markdown-to-HTML helper used by the admin WYSIWYG preview.
/// Accepts urlencoded `data` (the EasyMDE client) and multipart/form-data.
/// Public, no auth, no CSRF (no side effects) — same as the Python route.
pub async fn getmd(
    State(_state): State<AppState>,
    headers: HeaderMap,
    body: Body,
) -> Result<Response, WebError> {
    let content_type = headers
        .get(header::CONTENT_TYPE)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("")
        .to_string();
    let bytes = axum::body::to_bytes(body, 2 * 1024 * 1024)
        .await
        .map_err(|e| WebError::Internal(format!("read body: {e}")))?;

    let data = if content_type.starts_with("multipart/form-data") {
        parse_multipart_field(&bytes, parse_boundary(&content_type).as_deref(), "data")
            .unwrap_or_default()
    } else {
        let form: HashMap<String, String> =
            serde_urlencoded::from_bytes(bytes.as_ref()).unwrap_or_default();
        form.get("data").cloned().unwrap_or_default()
    };

    let html = domain::post::render_markdown(&data);
    Ok(Json(serde_json::json!({ "data": html })).into_response())
}

/// `GET /tags` and `GET /tags/` — tag cloud (full or htmx fragment). NOT cached.
pub async fn tags_index(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> Result<Response, WebError> {
    let tag_service = TagService::new(state.tags.clone());
    let tags = tag_service.get_all_tags().await?;
    let template = if is_htmx_request(&headers) {
        "tags.htmx"
    } else {
        "tags.html"
    };
    let body = render(&state.templates, template, context! { tags => tags })?;
    Ok(html_response(body))
}

/// `GET /tags/{alias}` — posts for a tag; 404 for unknown tags.
pub async fn tag_view(
    State(state): State<AppState>,
    Path(alias): Path<String>,
    headers: HeaderMap,
) -> Result<Response, WebError> {
    let tag_service = TagService::new(state.tags.clone());
    let Some(tag) = tag_service.get_tag_by_alias(&alias).await? else {
        return Ok(not_found());
    };
    let post_service = PostService::new(state.posts.clone());
    let posts = match tag.id {
        Some(id) => post_service.get_posts_by_tag(id).await?,
        None => Vec::new(),
    };
    let posts_by_year = group_posts_by_year(posts);
    let template = if is_htmx_request(&headers) {
        "posts.htmx"
    } else {
        "tag.html"
    };
    let body = render(
        &state.templates,
        template,
        context! { posts_by_year => posts_by_year, tag => tag },
    )?;
    Ok(html_response(body))
}

/// `GET /{alias}` — catch-all post/page view (cached, htmx-aware key).
/// Registered LAST so `/tags`, `/admin`, `/static` are never shadowed.
pub async fn post_view(
    State(state): State<AppState>,
    Path(alias): Path<String>,
    headers: HeaderMap,
    uri: Uri,
) -> Result<Response, WebError> {
    let key = htmx_key_builder(&path_query(&uri), &headers);
    with_cache(&state.cache, key, || async {
        let post_service = PostService::new(state.posts.clone());
        let Some(post) = post_service.get_post_by_alias(&alias).await? else {
            return Ok(not_found());
        };
        let is_published = post.publishedon.is_some();
        if !(is_published || post.is_page) {
            return Ok(not_found());
        }
        let tags = match post.id {
            Some(id) => post_service.get_tags_for_post(id).await?,
            None => Vec::new(),
        };
        let view = PostView::new(post);
        let template = if is_htmx_request(&headers) {
            "post.htmx"
        } else {
            "post.html"
        };
        let body = render(
            &state.templates,
            template,
            context! { post => view, tags => tags },
        )?;
        Ok(html_response(body))
    })
    .await
}

/// Extract the `boundary` parameter from a multipart Content-Type header.
fn parse_boundary(content_type: &str) -> Option<String> {
    content_type.split(';').find_map(|part| {
        let part = part.trim();
        part.strip_prefix("boundary=")
            .map(|v| v.trim().trim_matches('"').to_string())
    })
}

/// Minimal multipart parser: returns the value of the part whose
/// Content-Disposition name is `field`. Good enough for the `data` text field.
fn parse_multipart_field(body: &[u8], boundary: Option<&str>, field: &str) -> Option<String> {
    let boundary = boundary?;
    let text = std::str::from_utf8(body).ok()?;
    let marker = format!("name=\"{field}\"");
    let idx = text.find(&marker)?;
    let rest = &text[idx..];
    let header_end = rest.find("\r\n\r\n")?;
    let value_start = header_end + 4;
    let end_marker = format!("\r\n--{boundary}");
    let value_end = rest[value_start..].find(&end_marker)? + value_start;
    Some(rest[value_start..value_end].to_string())
}
