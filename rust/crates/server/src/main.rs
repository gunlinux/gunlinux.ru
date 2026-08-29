//! Server binary — wires persistence repositories into the web layer and
//! serves the axum application on port 8000.

use std::net::SocketAddr;
use std::sync::Arc;

use anyhow::Context;
use domain::{
    CategoryRepository, IconRepository, PostRepository, TagRepository, UserRepository,
    VisitRepository,
};
use persistence::migrator::{Migrator, MigratorTrait};
use persistence::repositories::{
    CategoryRepository as SeaCategoryRepository, IconRepository as SeaIconRepository,
    PostRepository as SeaPostRepository, TagRepository as SeaTagRepository,
    UserRepository as SeaUserRepository, VisitRepository as SeaVisitRepository,
};
use web::app::AppState;
use web::cache::Cache;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env().unwrap_or_else(|_| "info".into()),
        )
        .init();

    let settings = Arc::new(web::settings::get_settings().clone());

    // SECRET_KEY signs the admin JWT, the session-cookie HMAC, and the
    // analytics IP-hash salt. Refuse to boot with an unset or publicly-known
    // key: the settings fallback yields the default on any config error, so
    // this check also covers those cases.
    if !secret_key_is_safe(&settings.secret_key) {
        anyhow::bail!(
            "SECRET_KEY is unset or equals the known default; refusing to start \
             with a forgeable signing key. Set SECRET_KEY to a strong random value \
             (e.g. `openssl rand -hex 32`) in the environment or the repo `.env`."
        );
    }

    // PostgreSQL only (SQLite support was removed). DATABASE_URL is required —
    // the server has no embedded-DB fallback; production and dev both supply
    // it (host `.env` via docker --env-file, or the repo `.env` for local runs).
    let database_url = std::env::var("DATABASE_URL")
        .context("DATABASE_URL must be set (postgres:// connection string)")?;

    let db = persistence::pool::connect(&database_url)
        .await
        .with_context(|| format!("connect to database: {database_url}"))?;

    // Apply migrations (baseline). Production cutover stamps this on the
    // existing PostgreSQL DB rather than re-running schema creation.
    Migrator::up(&db, None)
        .await
        .context("apply database migrations")?;
    tracing::info!("migrations applied");

    let posts: Arc<dyn PostRepository> = Arc::new(SeaPostRepository::new(db.clone()));
    let tags: Arc<dyn TagRepository> = Arc::new(SeaTagRepository::new(db.clone()));
    let users: Arc<dyn UserRepository> = Arc::new(SeaUserRepository::new(db.clone()));
    let categories: Arc<dyn CategoryRepository> = Arc::new(SeaCategoryRepository::new(db.clone()));
    let icons: Arc<dyn IconRepository> = Arc::new(SeaIconRepository::new(db.clone()));
    let visits: Arc<dyn VisitRepository> = Arc::new(SeaVisitRepository::new(db.clone()));

    let mut state = AppState::new(
        posts,
        tags,
        users,
        categories,
        icons,
        visits,
        settings.clone(),
    );
    // Redis backend when REDIS_URL is set (in `.env` or the environment);
    // falls back to the in-memory cache otherwise or on connect failure.
    state.cache = Cache::connect(settings.redis_url.as_deref()).await;

    let addr: SocketAddr = std::env::var("BIND_ADDR")
        .unwrap_or_else(|_| "0.0.0.0:8000".to_string())
        .parse()
        .context("invalid BIND_ADDR")?;

    tracing::info!("starting gunlinux.ru (rust) on {addr}");
    web::app::run(state, addr).await.context("serve")?;
    Ok(())
}

/// Returns true when `secret` is a usable signing key: non-empty and not the
/// publicly-known default baked into `Settings::default()`. An unset
/// `SECRET_KEY` surfaces as the default after settings loading, so this check
/// rejects both directly.
fn secret_key_is_safe(secret: &str) -> bool {
    !secret.is_empty() && secret != web::settings::Settings::default().secret_key
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unset_secret_is_rejected() {
        assert!(!secret_key_is_safe(""));
    }

    #[test]
    fn default_secret_is_rejected() {
        assert!(!secret_key_is_safe(
            &web::settings::Settings::default().secret_key
        ));
    }

    #[test]
    fn custom_secret_is_accepted() {
        assert!(secret_key_is_safe("a-strong-random-value"));
    }
}
