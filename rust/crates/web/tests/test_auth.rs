//! Auth flow coverage (login, session cookie, admin redirects).

mod common;

use axum::http::StatusCode;
use common::{body_text, get, get_with_cookie, login_cookie, post_form, test_app};
use web::auth;

#[test]
fn test_jwt_roundtrip() {
    let settings = web::settings::Settings::default();
    let token = auth::create_access_token("testuser", &settings).unwrap();
    assert!(token.contains('.'));
    assert_eq!(
        auth::decode_token(&token, &settings).as_deref(),
        Some("testuser")
    );
}

#[test]
fn test_jwt_invalid() {
    let settings = web::settings::Settings::default();
    assert_eq!(auth::decode_token("not-a-valid-token", &settings), None);
}

#[tokio::test]
async fn test_admin_requires_login() {
    let (_store, app) = test_app();
    let resp = get(&app, "/admin").await;
    assert_eq!(resp.status(), StatusCode::FOUND);
    assert_eq!(resp.headers().get("location").unwrap(), "/admin/login");
}

#[tokio::test]
async fn test_admin_trailing_slash_requires_login() {
    // The admin index lives at /admin/ — both forms must redirect.
    let (_store, app) = test_app();
    let resp = get(&app, "/admin/").await;
    assert_eq!(resp.status(), StatusCode::FOUND);
    assert_eq!(resp.headers().get("location").unwrap(), "/admin/login");
}

#[tokio::test]
async fn test_admin_login_wrong_password() {
    let (store, app) = test_app();
    common::seed_user(&store, "admin", "right-password");

    let resp = post_form(&app, "/admin/login", "username=admin&password=wrong").await;
    assert_eq!(resp.status(), StatusCode::OK);
    let body = body_text(resp).await;
    assert!(body.contains("Invalid username or password"));
}

#[tokio::test]
async fn test_admin_login_flow() {
    let (store, app) = test_app();
    common::seed_user(&store, "admin", "right-password");

    let cookie = login_cookie(&app, "admin", "right-password").await;
    assert!(cookie.starts_with("session="), "cookie: {cookie}");

    // Dashboard reachable with the cookie.
    let resp = get_with_cookie(&app, "/admin", &cookie).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let body = body_text(resp).await;
    assert!(body.contains("Posts"));

    // Without the cookie, /admin redirects to login.
    let resp = get(&app, "/admin").await;
    assert_eq!(resp.status(), StatusCode::FOUND);
    assert_eq!(resp.headers().get("location").unwrap(), "/admin/login");
}

#[tokio::test]
async fn test_admin_logout_clears_cookie() {
    let (store, app) = test_app();
    common::seed_user(&store, "admin", "pw");
    let cookie = login_cookie(&app, "admin", "pw").await;

    let resp = get_with_cookie(&app, "/admin/logout", &cookie).await;
    assert_eq!(resp.status(), StatusCode::FOUND);
    let set_cookie = resp.headers().get("set-cookie").unwrap().to_str().unwrap();
    assert!(set_cookie.contains("Max-Age=0"), "cookie: {set_cookie}");
    assert!(set_cookie.starts_with("session=;"), "cookie: {set_cookie}");
}

#[tokio::test]
async fn test_session_cookie_is_tamper_evident() {
    let (_store, app) = test_app();
    // A forged/truncated session cookie must be treated as unauthenticated.
    let resp = get_with_cookie(&app, "/admin", "session=not.a.valid.signature").await;
    assert_eq!(resp.status(), StatusCode::FOUND);
}
