//! Server-side visit analytics: the tracking middleware records referrer
//! sources / landing pages per full-page load, and the admin stats page
//! renders them.

mod common;

use axum::body::Body;
use axum::http::{Request, StatusCode};
use axum::response::Response;
use common::{expect_status, get_with_cookie, login_cookie, seed_user, seed_visit, test_app};
use tower::ServiceExt;

/// A browser-like GET (Accept: text/html) with optional extra headers, so the
/// tracking middleware counts it.
fn html_get(uri: &str, extra_headers: &[(&str, &str)]) -> Request<Body> {
    let mut builder = Request::builder()
        .uri(uri)
        .header("accept", "text/html,application/xhtml+xml");
    for (name, value) in extra_headers {
        builder = builder.header(*name, *value);
    }
    builder.body(Body::empty()).unwrap()
}

async fn send(app: &axum::Router, req: Request<Body>) -> Response {
    app.clone().oneshot(req).await.unwrap()
}

#[tokio::test]
async fn test_referer_visit_is_recorded() {
    let (store, app) = test_app();
    let resp = send(
        &app,
        html_get(
            "/",
            &[
                ("referer", "https://habr.com/ru/articles/"),
                ("x-forwarded-for", "1.2.3.4"),
            ],
        ),
    )
    .await;
    assert_eq!(resp.status(), StatusCode::OK);

    let guard = store.lock().unwrap();
    assert_eq!(guard.visits.len(), 1);
    let visit = &guard.visits[0];
    // Referrer is normalized to the bare host; the landing path is recorded.
    assert_eq!(visit.referrer.as_deref(), Some("habr.com"));
    assert_eq!(visit.path, "/");
    let ip_hash = visit.ip_hash.clone().expect("ip hash recorded");
    assert_eq!(ip_hash.len(), 64);
    drop(guard);

    // Same IP on another page → identical salted hash, so unique-visitor
    // counts dedupe across pages.
    send(
        &app,
        html_get(
            "/posts",
            &[
                ("referer", "https://habr.com/ru/articles/"),
                ("x-forwarded-for", "1.2.3.4"),
            ],
        ),
    )
    .await;
    let guard = store.lock().unwrap();
    assert_eq!(guard.visits.len(), 2);
    assert_eq!(guard.visits[1].ip_hash.as_deref(), Some(ip_hash.as_str()));
}

#[tokio::test]
async fn test_direct_visit_has_no_referrer() {
    let (store, app) = test_app();
    send(&app, html_get("/", &[])).await;
    let guard = store.lock().unwrap();
    assert_eq!(guard.visits.len(), 1);
    assert_eq!(guard.visits[0].referrer, None);
    assert_eq!(guard.visits[0].path, "/");
}

#[tokio::test]
async fn test_non_page_requests_are_not_tracked() {
    let (store, app) = test_app();
    // htmx fragment swaps are navigations inside the site, not entries.
    let req = Request::builder()
        .uri("/")
        .header("accept", "text/html")
        .header("hx-request", "true")
        .body(Body::empty())
        .unwrap();
    send(&app, req).await;
    // Static assets, admin pages and machine endpoints never count.
    send(&app, html_get("/static/dist/css/bundle.css", &[])).await;
    send(&app, html_get("/admin", &[])).await;
    send(&app, html_get("/sitemap.xml", &[])).await;
    send(&app, html_get("/rss.xml", &[])).await;
    send(&app, html_get("/robots.txt", &[])).await;
    // Non-browser clients (curl, scripts, feeds) are not tracked.
    let req = Request::builder()
        .uri("/")
        .header("accept", "*/*")
        .body(Body::empty())
        .unwrap();
    send(&app, req).await;
    // POSTs are not page views.
    let req = Request::builder()
        .method("POST")
        .uri("/md/")
        .header("accept", "text/html")
        .header("content-type", "application/x-www-form-urlencoded")
        .body(Body::from("data=hello"))
        .unwrap();
    send(&app, req).await;

    let guard = store.lock().unwrap();
    assert!(
        guard.visits.is_empty(),
        "expected no visits, got {}",
        guard.visits.len()
    );
}

#[tokio::test]
async fn test_cached_page_loads_still_count_as_views() {
    let (store, app) = test_app();
    // The second request is served from the response cache, but the tracking
    // middleware runs before it — each load is one view.
    send(&app, html_get("/", &[])).await;
    send(&app, html_get("/", &[])).await;
    let guard = store.lock().unwrap();
    assert_eq!(guard.visits.len(), 2);
}

#[tokio::test]
async fn test_stats_requires_login() {
    let (_store, app) = test_app();
    let resp = send(&app, html_get("/admin/stats", &[])).await;
    assert_eq!(resp.status(), StatusCode::FOUND);
    assert_eq!(
        resp.headers().get("location").unwrap(),
        "/admin/login",
        "unauthenticated /admin/stats must redirect to login"
    );
}

#[tokio::test]
async fn test_stats_page_shows_sources_and_totals() {
    let (store, app) = test_app();
    seed_user(&store, "admin", "pw");
    seed_visit(&store, "/", Some("habr.com"), Some("h1"));
    seed_visit(&store, "/rust", Some("habr.com"), Some("h2"));
    seed_visit(&store, "/rust", None, Some("h1"));
    let cookie = login_cookie(&app, "admin", "pw").await;

    let body = expect_status(
        get_with_cookie(&app, "/admin/stats", &cookie).await,
        StatusCode::OK,
    )
    .await;
    // Top sources: habr.com (2) beats direct (1).
    assert!(body.contains("habr.com"), "got: {body}");
    assert!(body.contains("direct"), "got: {body}");
    assert!(body.contains("Top sources"), "got: {body}");
    assert!(body.contains("Top pages"), "got: {body}");
    // `/` renders HTML-escaped (`&#x2f;`), so match on the unescaped part.
    assert!(body.contains("rust"), "got: {body}");
    // Totals: 3 views all time, 3 in the last 30 days, 2 unique visitors.
    assert!(body.contains("Views, all time"), "got: {body}");
    assert!(body.contains("Unique visitors, 30 days"), "got: {body}");
    // The daily chart always renders 14 bars, one per day.
    assert_eq!(body.matches("stats-bar__label").count(), 14);
}

#[tokio::test]
async fn test_dashboard_shows_statistics_card() {
    let (store, app) = test_app();
    seed_user(&store, "admin", "pw");
    seed_visit(&store, "/", None, Some("h1"));
    let cookie = login_cookie(&app, "admin", "pw").await;

    let body = expect_status(
        get_with_cookie(&app, "/admin", &cookie).await,
        StatusCode::OK,
    )
    .await;
    assert!(body.contains("Statistics"), "got: {body}");
    assert!(body.contains("/admin/stats"), "got: {body}");
}
