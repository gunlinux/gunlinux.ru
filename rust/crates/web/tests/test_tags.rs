//! Tag route behaviors (`tests/test_tags.py` is "migrated — covered by new
//! test files", so this file is the Rust coverage for the tag endpoints).

mod common;

use axum::http::StatusCode;
use common::{body_text, expect_status, get, get_hx, seed_published_post, seed_tag, test_app};

#[tokio::test]
async fn test_tag_lists_posts_for_tag() {
    let (store, app) = test_app();
    seed_published_post(&store, "Rust Post", "rust-post", "x");
    seed_tag(&store, "Rust", "rust");
    // Link the post to the tag through the m2m association.
    {
        let mut store = store.lock().unwrap();
        let post_id = store
            .posts
            .iter()
            .find(|p| p.alias == "rust-post")
            .unwrap()
            .id
            .unwrap();
        let tag_id = store
            .tags
            .iter()
            .find(|t| t.alias == "rust")
            .unwrap()
            .id
            .unwrap();
        store.post_tags.push((post_id, tag_id));
    }

    let body = expect_status(get(&app, "/tags/rust").await, StatusCode::OK).await;
    assert!(body.contains("Rust Post"));
}

#[tokio::test]
async fn test_tag_view_htmx_fragment() {
    let (store, app) = test_app();
    seed_published_post(&store, "Htmx Tag Post", "htmx-tag-post", "x");
    seed_tag(&store, "Htmx", "htmx");
    {
        let mut store = store.lock().unwrap();
        let post_id = store
            .posts
            .iter()
            .find(|p| p.alias == "htmx-tag-post")
            .unwrap()
            .id
            .unwrap();
        let tag_id = store
            .tags
            .iter()
            .find(|t| t.alias == "htmx")
            .unwrap()
            .id
            .unwrap();
        store.post_tags.push((post_id, tag_id));
    }

    // Full page: tag.html extends layout.
    let full = body_text(get(&app, "/tags/htmx").await).await;
    assert!(full.contains("<!DOCTYPE"));
    assert!(full.contains("Посты с тэгом: Htmx"));

    // htmx: posts.htmx fragment.
    let fragment = body_text(get_hx(&app, "/tags/htmx").await).await;
    assert!(!fragment.contains("<!DOCTYPE"));
    assert!(fragment.contains("Htmx Tag Post"));
}

#[tokio::test]
async fn test_tags_index_htmx_fragment() {
    let (store, app) = test_app();
    seed_tag(&store, "Linux", "linux");

    let fragment = body_text(get_hx(&app, "/tags").await).await;
    assert!(!fragment.contains("<!DOCTYPE"));
    assert!(fragment.contains("Linux"));
}
