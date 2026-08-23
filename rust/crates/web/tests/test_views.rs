//! Port of `tests/test_views.py`.

mod common;

use axum::http::StatusCode;
use common::{
    body_text, expect_status, get, get_hx, post_form, seed_page, seed_published_post, seed_tag,
    test_app,
};
use domain::Post;

#[tokio::test]
async fn test_published_post_view() {
    let (store, app) = test_app();
    seed_published_post(&store, "My View Post", "my-view-post", "# Hello");

    let resp = get(&app, "/my-view-post").await;
    assert_eq!(resp.status(), StatusCode::OK);
    let body = body_text(resp).await;
    assert!(body.contains("My View Post"));
    // Markdown rendered into the post body.
    assert!(body.contains("<h1>Hello</h1>"));
}

#[tokio::test]
async fn test_unpublished_post_is_404() {
    let (store, app) = test_app();
    // Post without publishedon and not a page.
    {
        let mut store = store.lock().unwrap();
        store
            .posts
            .push(Post::new("Draft", "draft-view-post", "secret"));
    }

    expect_status(get(&app, "/draft-view-post").await, StatusCode::NOT_FOUND).await;
    // 404 body matches FastAPI's default HTTPException JSON.
    let body = body_text(get(&app, "/draft-view-post").await).await;
    assert_eq!(body, "{\"detail\":\"Not Found\"}");
}

#[tokio::test]
async fn test_page_view() {
    let (store, app) = test_app();
    seed_page(&store, "About", "about");

    let body = expect_status(get(&app, "/about").await, StatusCode::OK).await;
    assert!(body.contains("About"));
    // Pages render their content too.
    assert!(body.contains("page content"));
}

#[tokio::test]
async fn test_tag_view() {
    let (store, app) = test_app();
    seed_tag(&store, "Python", "python-view");

    let resp = get(&app, "/tags/python-view").await;
    assert_eq!(resp.status(), StatusCode::OK);
    let body = body_text(resp).await;
    assert!(body.contains("Python"));
}

#[tokio::test]
async fn test_tag_not_found() {
    let (_store, app) = test_app();
    expect_status(
        get(&app, "/tags/nonexistent-xyz").await,
        StatusCode::NOT_FOUND,
    )
    .await;
    // 404 body matches FastAPI's default HTTPException JSON.
    let body = body_text(get(&app, "/tags/nonexistent-xyz").await).await;
    assert_eq!(body, "{\"detail\":\"Not Found\"}");
}

#[tokio::test]
async fn test_tags_index_with_slash() {
    let (_store, app) = test_app();
    expect_status(get(&app, "/tags/").await, StatusCode::OK).await;
}

#[tokio::test]
async fn test_tags_index_without_slash() {
    let (_store, app) = test_app();
    // The catch-all GET /{alias} must not swallow /tags.
    expect_status(get(&app, "/tags").await, StatusCode::OK).await;
}

#[tokio::test]
async fn test_markdown_endpoint() {
    let (_store, app) = test_app();
    let resp = post_form(&app, "/md/", "data=%23+Title").await;
    assert_eq!(resp.status(), StatusCode::OK);
    let body = body_text(resp).await;
    let json: serde_json::Value = serde_json::from_str(&body).unwrap();
    assert!(json["data"].as_str().unwrap().contains("Title"));
}

#[tokio::test]
async fn test_markdown_endpoint_renders_fence_as_inline_code() {
    // Matches python-markdown without fenced_code (the Python /md/ route):
    // the fence becomes an inline <code> span, language tag first.
    let (_store, app) = test_app();
    let resp = post_form(
        &app,
        "/md/",
        "data=%60%60%60rust%0Afn+main()%7B%7D%0A%60%60%60",
    )
    .await;
    let body = body_text(resp).await;
    let json: serde_json::Value = serde_json::from_str(&body).unwrap();
    assert_eq!(
        json["data"].as_str().unwrap(),
        "<p><code>rust\nfn main(){}</code></p>"
    );
}

#[tokio::test]
async fn test_rss_includes_teaser() {
    let (store, app) = test_app();
    seed_published_post(
        &store,
        "Feed Post",
        "feed-post",
        "A short teaser sentence.\n\nSecond paragraph.",
    );

    let body = expect_status(get(&app, "/rss.xml").await, StatusCode::OK).await;
    assert!(body.contains("A short teaser sentence."));
    assert!(!body.contains("Second paragraph."));
}

#[test]
fn test_post_teaser_truncates() {
    let post = Post::new("t", "a", "x".repeat(500));
    let teaser = post.teaser();
    assert!(teaser.ends_with('…'));
    assert!(teaser.chars().count() <= 301);
}

#[tokio::test]
async fn test_htmx_pages() {
    let (_store, app) = test_app();
    let resp = get(&app, "/hx/pages").await;
    assert_eq!(resp.status(), StatusCode::OK);
    assert!(!body_text(resp).await.contains("<!DOCTYPE"));
}

#[tokio::test]
async fn test_htmx_icons() {
    let (_store, app) = test_app();
    let resp = get(&app, "/hx/icons").await;
    assert_eq!(resp.status(), StatusCode::OK);
    assert!(!body_text(resp).await.contains("<!DOCTYPE"));
}

#[tokio::test]
async fn test_htmx_dual_mode_posts() {
    let (store, app) = test_app();
    seed_published_post(&store, "Htmx Post", "htmx-post", "body");

    // Both the full page (posts.html) and the fragment (posts.htmx) are bare
    // listings in the Python app — posts.html has no {% extends layout %}.
    let full = body_text(get(&app, "/posts").await).await;
    assert!(!full.contains("<!DOCTYPE"));
    assert!(full.contains("postGroup"));
    assert!(full.contains("Htmx Post"));

    let fragment = body_text(get_hx(&app, "/posts").await).await;
    assert!(!fragment.contains("<!DOCTYPE"));
    assert!(fragment.contains("postGroup"));
    assert!(fragment.contains("Htmx Post"));
}

#[tokio::test]
async fn test_htmx_dual_mode_post() {
    let (store, app) = test_app();
    seed_published_post(&store, "Dual Post", "dual-post", "## Sub");

    let full = body_text(get(&app, "/dual-post").await).await;
    assert!(full.contains("<!DOCTYPE"));
    assert!(full.contains("<h2>Sub</h2>"));

    let fragment = body_text(get_hx(&app, "/dual-post").await).await;
    assert!(!fragment.contains("<!DOCTYPE"));
    assert!(fragment.contains("Dual Post"));
}

#[tokio::test]
async fn test_cache_serves_cached_body() {
    let (store, app) = test_app();
    seed_published_post(&store, "First Title", "cached-post", "x");

    let first = body_text(get(&app, "/cached-post").await).await;
    assert!(first.contains("First Title"));

    // Mutate the underlying post; the cached response must still be served.
    {
        let mut store = store.lock().unwrap();
        let post = store
            .posts
            .iter_mut()
            .find(|p| p.alias == "cached-post")
            .unwrap();
        post.pagetitle = "Changed Title".to_string();
    }

    let second = body_text(get(&app, "/cached-post").await).await;
    assert!(second.contains("First Title"));
}
