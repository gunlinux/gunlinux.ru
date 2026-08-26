//! Web layer: axum application (routes, templates, auth, admin, caching).
//! Depends only on `domain` traits — persistence implementations are injected
//! through `AppState` (the `server` binary wires them).

pub mod admin;
pub mod analytics;
pub mod app;
pub mod auth;
pub mod cache;
pub mod error;
pub mod routes;
pub mod settings;
pub mod templates;

pub use app::{build_app, build_app_with_static, run, AppState};
pub use error::WebError;
