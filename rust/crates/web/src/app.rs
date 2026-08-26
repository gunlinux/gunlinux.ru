//! App factory.
//!
//! Critical ordering constraint: `/static`, `/tags` and `/admin` are
//! registered BEFORE the catch-all `GET /{alias}`, which is registered last
//! so it never shadows them.

use std::net::SocketAddr;
use std::sync::Arc;

use axum::routing::{get, post};
use axum::Router;
use minijinja::{Environment, Value};
use tower_http::services::ServeDir;
use tower_http::trace::TraceLayer;

use crate::admin;
use crate::analytics;
use crate::cache::Cache;
use crate::routes;
use crate::settings::Settings;
use crate::templates::build_env;
use domain::{
    CategoryRepository, IconRepository, PostRepository, TagRepository, UserRepository,
    VisitRepository,
};

/// Everything the HTTP layer needs, injected by the `server` binary.
/// All data access goes through the domain repository trait objects.
#[derive(Clone)]
pub struct AppState {
    pub posts: Arc<dyn PostRepository>,
    pub tags: Arc<dyn TagRepository>,
    pub users: Arc<dyn UserRepository>,
    pub categories: Arc<dyn CategoryRepository>,
    pub icons: Arc<dyn IconRepository>,
    pub visits: Arc<dyn VisitRepository>,
    pub settings: Arc<Settings>,
    pub cache: Cache,
    pub templates: Arc<Environment<'static>>,
}

impl AppState {
    /// Convenience constructor used by tests: fresh in-memory response cache
    /// (no shared state between tests) and a template environment for
    /// `settings`. The `server` binary swaps in a Redis-backed cache via
    /// [`Cache::connect`] when `REDIS_URL` is configured.
    pub fn new(
        posts: Arc<dyn PostRepository>,
        tags: Arc<dyn TagRepository>,
        users: Arc<dyn UserRepository>,
        categories: Arc<dyn CategoryRepository>,
        icons: Arc<dyn IconRepository>,
        visits: Arc<dyn VisitRepository>,
        settings: Arc<Settings>,
    ) -> Self {
        Self {
            posts,
            tags,
            users,
            categories,
            icons,
            visits,
            templates: Arc::new(build_env(settings.clone())),
            cache: Cache::memory(),
            settings,
        }
    }
}

/// Assemble the full router. The `templates` field is built from the settings
/// unless provided (tests may pass their own).
pub fn build_app(state: AppState) -> Router {
    // Static files: `app/static` (repo root) by default, overridable via
    // STATIC_DIR.
    let static_dir = std::env::var("STATIC_DIR").unwrap_or_else(|_| "app/static".to_string());
    build_app_with_static(state, &static_dir)
}

/// Like [`build_app`], but with an explicit static-file directory. Tests use
/// this to point at the repo's `app/static` regardless of the cwd.
pub fn build_app_with_static(state: AppState, static_dir: &str) -> Router {
    // Inline the built stylesheet into every rendered page: the bundle is
    // ~6.6 KiB, so embedding it removes a render-blocking request from the
    // critical path. `dist/` is gitignored, so when the CSS has not been
    // built (`make css-build`) the template falls back to the external
    // <link>.
    let css_path = format!("{static_dir}/dist/css/bundle.css");
    let inline_css = match std::fs::read_to_string(&css_path) {
        Ok(css) => css,
        Err(e) => {
            tracing::warn!(
                "cannot read {css_path} for inlining ({e}); falling back to external stylesheet"
            );
            String::new()
        }
    };

    let mut state = state;
    let mut env = build_env(state.settings.clone());
    env.add_global("inline_css", Value::from_safe_string(inline_css));
    state.templates = Arc::new(env);

    Router::new()
        .route("/", get(routes::index))
        .route("/posts", get(routes::posts))
        .route("/hx/icons", get(routes::icons_hx))
        .route("/robots.txt", get(routes::robots))
        .route("/sitemap.xml", get(routes::sitemap))
        .route("/rss.xml", get(routes::rss))
        .route("/md/", post(routes::getmd))
        .route("/tags", get(routes::tags_index))
        .route("/tags/", get(routes::tags_index))
        .route("/tags/{alias}", get(routes::tag_view))
        .nest_service("/static", ServeDir::new(static_dir))
        .merge(admin::router())
        // Catch-all must stay last.
        .route("/{alias}", get(routes::post_view))
        .layer(axum::middleware::from_fn_with_state(
            state.clone(),
            analytics::track_visit,
        ))
        .layer(TraceLayer::new_for_http())
        .with_state(state)
}

/// Bind `addr` and serve the app (used by the `server` binary). Connect info
/// is exposed so the visit-tracking middleware can capture the client IP
/// (salted-hashed) when no `X-Forwarded-For` header is present.
pub async fn run(state: AppState, addr: SocketAddr) -> std::io::Result<()> {
    let listener = tokio::net::TcpListener::bind(addr).await?;
    tracing::info!("listening on {addr}");
    let app = build_app(state).into_make_service_with_connect_info::<SocketAddr>();
    axum::serve(listener, app).await
}
