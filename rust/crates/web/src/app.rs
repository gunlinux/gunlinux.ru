//! App factory — mirrors `app/core/application.py::create_app`.
//!
//! Critical ordering constraint (ported from the Python app): `/static`,
//! `/tags` and `/admin` are registered BEFORE the catch-all `GET /{alias}`,
//! which is registered last so it never shadows them.

use std::net::SocketAddr;
use std::sync::Arc;

use axum::routing::{get, post};
use axum::Router;
use minijinja::Environment;
use tower_http::services::ServeDir;
use tower_http::trace::TraceLayer;

use crate::admin;
use crate::cache::Cache;
use crate::routes;
use crate::settings::Settings;
use crate::templates::build_env;
use domain::{CategoryRepository, IconRepository, PostRepository, TagRepository, UserRepository};

/// Everything the HTTP layer needs, injected by the `server` binary.
/// All data access goes through the domain repository trait objects.
#[derive(Clone)]
pub struct AppState {
    pub posts: Arc<dyn PostRepository>,
    pub tags: Arc<dyn TagRepository>,
    pub users: Arc<dyn UserRepository>,
    pub categories: Arc<dyn CategoryRepository>,
    pub icons: Arc<dyn IconRepository>,
    pub settings: Arc<Settings>,
    pub cache: Cache,
    pub templates: Arc<Environment<'static>>,
}

impl AppState {
    /// Convenience constructor used by tests: fresh response cache (no shared
    /// state between tests) and a template environment for `settings`.
    pub fn new(
        posts: Arc<dyn PostRepository>,
        tags: Arc<dyn TagRepository>,
        users: Arc<dyn UserRepository>,
        categories: Arc<dyn CategoryRepository>,
        icons: Arc<dyn IconRepository>,
        settings: Arc<Settings>,
    ) -> Self {
        Self {
            posts,
            tags,
            users,
            categories,
            icons,
            templates: Arc::new(build_env(settings.clone())),
            cache: Cache::new(),
            settings,
        }
    }
}

/// Assemble the full router. The `templates` field is built from the settings
/// unless provided (tests may pass their own).
pub fn build_app(state: AppState) -> Router {
    // Static files: `app/static` (repo root) by default, overridable via
    // STATIC_DIR (mirrors `app.mount("/static", StaticFiles(...))`).
    let static_dir = std::env::var("STATIC_DIR").unwrap_or_else(|_| "app/static".to_string());

    Router::new()
        .route("/", get(routes::index))
        .route("/posts", get(routes::posts))
        .route("/hx/pages", get(routes::pages_hx))
        .route("/hx/icons", get(routes::icons_hx))
        .route("/robots.txt", get(routes::robots))
        .route("/sitemap.xml", get(routes::sitemap))
        .route("/rss.xml", get(routes::rss))
        .route("/md/", post(routes::getmd))
        .route("/tags", get(routes::tags_index))
        .route("/tags/", get(routes::tags_index))
        .route("/tags/{alias}", get(routes::tag_view))
        .nest_service("/static", ServeDir::new(&static_dir))
        .merge(admin::router())
        // Catch-all must stay last.
        .route("/{alias}", get(routes::post_view))
        .layer(TraceLayer::new_for_http())
        .with_state(state)
}

/// Bind `addr` and serve the app (used by the `server` binary).
pub async fn run(state: AppState, addr: SocketAddr) -> std::io::Result<()> {
    let listener = tokio::net::TcpListener::bind(addr).await?;
    tracing::info!("listening on {addr}");
    axum::serve(listener, build_app(state)).await
}
