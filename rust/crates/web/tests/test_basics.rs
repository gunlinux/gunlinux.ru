//! Basic route tests (robots, 404, static).

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
    // Exact body contract.
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
    // The pinned 404 contract.
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
    let resp = get(&app, "/static/missing-file.css").await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
    let body = body_text(resp).await;
    assert!(!body.contains("postGroup"));
}

/// The served CSS bundle must reserve the vertical scrollbar gutter
/// (`scrollbar-gutter: stable` on `html`). Without it the centered layout
/// (header included) shifts ~half a scrollbar-width left when htmx swaps in
/// a page tall enough to scroll. The rule lives in `app/static/src/global/
/// reboot.css`; this test also fails when the bundle is stale (CSS changed
/// but `make css-build` not re-run).
#[tokio::test]
async fn test_css_bundle_reserves_scrollbar_gutter() {
    let (_store, app) = test_app();
    let body = expect_status(
        get(&app, "/static/dist/css/bundle.css").await,
        StatusCode::OK,
    )
    .await;
    assert!(
        body.contains("scrollbar-gutter:stable"),
        "bundle.css must contain `scrollbar-gutter:stable` — rebuild with `make css-build` \
         if reboot.css was changed"
    );
}
