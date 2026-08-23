//! Port of `tests/test_basics.py`.

mod common;

use axum::http::StatusCode;
use common::{body_text, expect_status, get, test_app};

#[tokio::test]
async fn test_index() {
    let (_store, app) = test_app();
    let body = expect_status(get(&app, "/").await, StatusCode::OK).await;
    assert!(body.contains("Неразумный перфекционизм"));
}

#[tokio::test]
async fn test_posts() {
    let (_store, app) = test_app();
    expect_status(get(&app, "/posts").await, StatusCode::OK).await;
}

#[tokio::test]
async fn test_tags() {
    let (_store, app) = test_app();
    expect_status(get(&app, "/tags/").await, StatusCode::OK).await;
}

#[tokio::test]
async fn test_robots() {
    let (_store, app) = test_app();
    let body = expect_status(get(&app, "/robots.txt").await, StatusCode::OK).await;
    assert!(body.contains("User-agent"));
    // Exact body from the Python route.
    assert_eq!(
        body,
        "\nUser-agent: *\nCrawl-delay: 2\nDisallow: /tags/*\nHost: gunlinux.ru\n"
    );
}

#[tokio::test]
async fn test_rss() {
    let (_store, app) = test_app();
    let resp = get(&app, "/rss.xml").await;
    assert_eq!(resp.status(), StatusCode::OK);
    assert_eq!(
        resp.headers().get("content-type").unwrap(),
        "application/rss+xml"
    );
}

#[tokio::test]
async fn test_sitemap() {
    let (_store, app) = test_app();
    let resp = get(&app, "/sitemap.xml").await;
    assert_eq!(resp.status(), StatusCode::OK);
    assert_eq!(
        resp.headers().get("content-type").unwrap(),
        "application/xml"
    );
}

#[tokio::test]
async fn test_404() {
    let (_store, app) = test_app();
    let resp = get(&app, "/nonexistent-alias-xyz").await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
    // Body matches FastAPI's default HTTPException handler exactly.
    let body = body_text(resp).await;
    assert_eq!(body, "{\"detail\":\"Not Found\"}");
    assert_eq!(
        get(&app, "/nonexistent-alias-xyz")
            .await
            .headers()
            .get("content-type")
            .unwrap(),
        "application/json"
    );
}

#[tokio::test]
async fn test_catch_all_does_not_shadow_tags_or_static() {
    let (_store, app) = test_app();
    expect_status(get(&app, "/tags").await, StatusCode::OK).await;
    // /static is mounted; a missing file inside it is a 404, not the catch-all.
    let resp = get(&app, "/static/dist/css/bundle.css").await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
    let body = body_text(resp).await;
    assert!(!body.contains("postGroup"));
}
