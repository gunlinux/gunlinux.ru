//! Shared repository test harness (plan.md §3 Thread A — platform-independent
//! tests).
//!
//! The suite bodies live in [`suite`] and take a `&DatabaseConnection`, so the
//! exact same assertions run against SQLite (default, fast, CI) and against
//! PostgreSQL (opt-in, behind the `postgres-parity` feature). The per-backend
//! test files (`tests/repositories.rs` and `tests/parity_postgres.rs`) only
//! differ in how they obtain a migrated database.

pub mod suite;

use persistence::migrator::{Migrator, MigratorTrait};
use persistence::pool;
use sea_orm::DatabaseConnection;

// Each integration-test binary compiles the whole `common` module tree, but
// only uses the backend helpers relevant to it — hence the allows below:
// `sqlite_db` is unused when only the parity binary is built, and `postgres`
// is unused when the (feature-on) SQLite binary is built.

/// Connect to a temp-file SQLite DB and apply all migrations.
/// The `NamedTempFile` is kept alive by the caller for the test's lifetime.
#[cfg_attr(feature = "postgres-parity", allow(dead_code))]
pub async fn sqlite_db() -> (DatabaseConnection, tempfile::NamedTempFile) {
    let file = tempfile::NamedTempFile::new().expect("create temp sqlite file");
    let url = format!("sqlite://{}?mode=rwc", file.path().display());
    let db = pool::connect(&url).await.expect("connect sqlite");
    Migrator::up(&db, None).await.expect("run migrations");
    (db, file)
}

#[cfg(feature = "postgres-parity")]
#[allow(dead_code)]
pub mod postgres;
