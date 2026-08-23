//! Admin panel: generic CRUD through the repository layer + cache invalidation
//! on every write (port of `CacheClearingModelView`).

mod common;

use axum::http::StatusCode;
use common::{
    body_text, expect_status, get, get_with_cookie, login_cookie, post_form_with_cookie,
    seed_published_post, seed_user, test_app,
};

#[tokio::test]
async fn test_admin_post_list() {
    let (store, app) = test_app();
    seed_user(&store, "admin", "pw");
    let cookie = login_cookie(&app, "admin", "pw").await;

    let body = expect_status(
        get_with_cookie(&app, "/admin/post/", &cookie).await,
        StatusCode::OK,
    )
    .await;
    assert!(body.contains("pagetitle"));
}

#[tokio::test]
async fn test_admin_unknown_model_404() {
    let (store, app) = test_app();
    seed_user(&store, "admin", "pw");
    let cookie = login_cookie(&app, "admin", "pw").await;
    expect_status(
        get_with_cookie(&app, "/admin/nope/", &cookie).await,
        StatusCode::NOT_FOUND,
    )
    .await;
}

#[tokio::test]
async fn test_admin_create_post_invalidates_cache() {
    let (store, app) = test_app();
    seed_user(&store, "admin", "pw");
    // Pre-fill the cache with a /posts listing that does not include the post.
    let before = body_text(get(&app, "/posts").await).await;
    assert!(!before.contains("Cache-Breaking Post"));

    let cookie = login_cookie(&app, "admin", "pw").await;
    let form = "pagetitle=Cache-Breaking+Post&alias=cache-breaking&content=%23+Hi&publishedon=2026-08-23T12%3A00%3A00Z&category_id=";
    let resp = post_form_with_cookie(&app, "/admin/post/create", form, &cookie).await;
    assert_eq!(resp.status(), StatusCode::SEE_OTHER);

    // The write must have invalidated the "blog" namespace: /posts now shows it.
    let after = body_text(get(&app, "/posts").await).await;
    assert!(after.contains("Cache-Breaking Post"));
    assert!(after.contains("cache-breaking"));
}

#[tokio::test]
async fn test_admin_edit_post_invalidates_cache() {
    let (store, app) = test_app();
    seed_user(&store, "admin", "pw");
    seed_published_post(&store, "Before Title", "edit-me", "x");
    let post_id = {
        let store = store.lock().unwrap();
        store
            .posts
            .iter()
            .find(|p| p.alias == "edit-me")
            .unwrap()
            .id
            .unwrap()
    };

    // Warm the cache.
    let before = body_text(get(&app, "/edit-me").await).await;
    assert!(before.contains("Before Title"));

    let cookie = login_cookie(&app, "admin", "pw").await;
    let form = "pagetitle=After+Title&alias=edit-me&content=updated&publishedon=2026-08-23T12%3A00%3A00Z&category_id=";
    let resp =
        post_form_with_cookie(&app, &format!("/admin/post/{post_id}/edit"), form, &cookie).await;
    assert_eq!(resp.status(), StatusCode::SEE_OTHER);

    let after = body_text(get(&app, "/edit-me").await).await;
    assert!(after.contains("After Title"));
}

#[tokio::test]
async fn test_admin_delete_post_invalidates_cache() {
    let (store, app) = test_app();
    seed_user(&store, "admin", "pw");
    seed_published_post(&store, "Doomed", "doomed-post", "x");
    let post_id = {
        let store = store.lock().unwrap();
        store
            .posts
            .iter()
            .find(|p| p.alias == "doomed-post")
            .unwrap()
            .id
            .unwrap()
    };

    // Warm the cache.
    let before = body_text(get(&app, "/doomed-post").await).await;
    assert!(before.contains("Doomed"));
    assert!(before.contains("<!DOCTYPE"));

    let cookie = login_cookie(&app, "admin", "pw").await;
    let resp =
        post_form_with_cookie(&app, &format!("/admin/post/{post_id}/delete"), "", &cookie).await;
    assert_eq!(resp.status(), StatusCode::SEE_OTHER);

    let after = get(&app, "/doomed-post").await;
    assert_eq!(after.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_admin_create_user_hashes_password() {
    let (store, app) = test_app();
    seed_user(&store, "admin", "pw");
    let cookie = login_cookie(&app, "admin", "pw").await;

    let form = "name=alice&password=s3cret&authenticated=";
    let resp = post_form_with_cookie(&app, "/admin/user/create", form, &cookie).await;
    assert_eq!(resp.status(), StatusCode::SEE_OTHER);

    // The stored password is a bcrypt hash, not the plaintext.
    let stored = {
        let store = store.lock().unwrap();
        store
            .users
            .iter()
            .find(|u| u.name == "alice")
            .unwrap()
            .password
            .clone()
    };
    assert_ne!(stored, "s3cret");
    assert!(
        stored.starts_with("$2"),
        "expected bcrypt hash, got {stored}"
    );
    assert!(domain::security::verify_password("s3cret", &stored));
}

#[tokio::test]
async fn test_admin_edit_user_keeps_password_when_blank() {
    let (store, app) = test_app();
    seed_user(&store, "admin", "pw");
    let cookie = login_cookie(&app, "admin", "pw").await;

    let stored_before = {
        let store = store.lock().unwrap();
        store
            .users
            .iter()
            .find(|u| u.name == "admin")
            .unwrap()
            .password
            .clone()
    };

    // Editing without a password must keep the existing hash.
    let form = "name=admin&password=&authenticated=";
    let resp = post_form_with_cookie(&app, "/admin/user/1/edit", form, &cookie).await;
    assert_eq!(resp.status(), StatusCode::SEE_OTHER);

    let stored_after = {
        let store = store.lock().unwrap();
        store
            .users
            .iter()
            .find(|u| u.name == "admin")
            .unwrap()
            .password
            .clone()
    };
    assert_eq!(stored_before, stored_after);
}

#[tokio::test]
async fn test_admin_edit_form_hides_password() {
    let (store, app) = test_app();
    seed_user(&store, "admin", "pw");
    let cookie = login_cookie(&app, "admin", "pw").await;

    let body = expect_status(
        get_with_cookie(&app, "/admin/user/1/edit", &cookie).await,
        StatusCode::OK,
    )
    .await;
    // The password input must not be rendered on edit.
    assert!(!body.contains("name=\"password\""));
}

#[tokio::test]
async fn test_admin_create_tag_and_category() {
    let (store, app) = test_app();
    seed_user(&store, "admin", "pw");
    let cookie = login_cookie(&app, "admin", "pw").await;

    let resp =
        post_form_with_cookie(&app, "/admin/tag/create", "title=Ops&alias=ops", &cookie).await;
    assert_eq!(resp.status(), StatusCode::SEE_OTHER);

    let resp = post_form_with_cookie(
        &app,
        "/admin/category/create",
        "title=Pages&alias=pages&template=&page=on",
        &cookie,
    )
    .await;
    assert_eq!(resp.status(), StatusCode::SEE_OTHER);

    {
        let store = store.lock().unwrap();
        assert!(store.tags.iter().any(|t| t.alias == "ops"));
        let cat = store
            .categories
            .iter()
            .find(|c| c.alias == "pages")
            .unwrap();
        assert_eq!(cat.page, Some(true));
    }
}

#[tokio::test]
async fn test_markdown_multipart() {
    let (_store, app) = test_app();
    let boundary = "----testboundary";
    let body = format!(
        "--{boundary}\r\nContent-Disposition: form-data; name=\"data\"\r\n\r\n# Multi\r\n--{boundary}--\r\n"
    );
    let resp = app
        .clone()
        .oneshot(
            axum::http::Request::builder()
                .method("POST")
                .uri("/md/")
                .header(
                    "content-type",
                    format!("multipart/form-data; boundary={boundary}"),
                )
                .body(axum::body::Body::from(body))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
    let text = body_text(resp).await;
    let json: serde_json::Value = serde_json::from_str(&text).unwrap();
    assert!(json["data"].as_str().unwrap().contains("<h1>Multi</h1>"));
}

use tower::ServiceExt;
