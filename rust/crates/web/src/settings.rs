//! Application settings.
//!
//! Semantics:
//! - defaults below apply when neither `.env` nor the environment provides a value;
//! - environment variables override the `.env` file (via `dotenvy`, which never
//!   overwrites already-set variables) — the `config` `Environment` source then
//!   reads the merged process environment;
//! - extra keys (unknown env vars / `.env` entries) are ignored;
//! - key names are matched case-insensitively against the uppercased env vars
//!   (`DATABASE_URL` ↔ `database_url`).
//!
//! Loaded once and cached in a `OnceLock`.

use std::sync::OnceLock;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct Settings {
    pub env: String,
    pub secret_key: String,
    pub database_url: String,
    pub yandex_verification: Option<String>,
    pub jwt_algorithm: String,
    pub jwt_expire_minutes: i64,
    /// Response-cache backend: Redis URL when set, in-memory cache otherwise.
    pub redis_url: Option<String>,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            env: "development".to_string(),
            secret_key: "hard-to-guess-string-change-in-production".to_string(),
            database_url: "postgres://postgres:postgres@localhost:5432/gunlinux".to_string(),
            yandex_verification: None,
            jwt_algorithm: "HS256".to_string(),
            jwt_expire_minutes: 60 * 24,
            redis_url: None,
        }
    }
}

static SETTINGS: OnceLock<Settings> = OnceLock::new();

/// Load settings once and cache them (mirrors `@lru_cache get_settings`).
///
/// `database_url` is informational only: the `server` crate owns the DB
/// connection and reads it from `DATABASE_URL` itself.
pub fn get_settings() -> &'static Settings {
    SETTINGS.get_or_init(load_settings)
}

fn load_settings() -> Settings {
    // Load `.env` into the process environment without overriding variables
    // that are already set (precedence: env vars > .env file).
    let _ = dotenvy::dotenv();

    config::Config::builder()
        .add_source(config::Environment::default().try_parsing(true))
        .build()
        .and_then(|c| c.try_deserialize::<Settings>())
        .unwrap_or_else(|e| {
            tracing::warn!("failed to load settings from environment, using defaults: {e}");
            Settings::default()
        })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn defaults() {
        let s = Settings::default();
        assert_eq!(s.env, "development");
        assert_eq!(s.secret_key, "hard-to-guess-string-change-in-production");
        assert_eq!(
            s.database_url,
            "postgres://postgres:postgres@localhost:5432/gunlinux"
        );
        assert_eq!(s.yandex_verification, None);
        assert_eq!(s.jwt_algorithm, "HS256");
        assert_eq!(s.jwt_expire_minutes, 1440);
        assert_eq!(s.redis_url, None);
    }
}
