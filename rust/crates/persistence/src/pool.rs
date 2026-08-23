//! Database connection helpers.

use sea_orm::{Database, DatabaseConnection, DbErr};

/// Connect to a database. Works for both `sqlite://...` and `postgres://...`
/// URLs (both the `sqlx-sqlite` and `sqlx-postgres` features are enabled on
/// the `sea-orm` dependency).
pub async fn connect(database_url: &str) -> Result<DatabaseConnection, DbErr> {
    Database::connect(database_url).await
}
