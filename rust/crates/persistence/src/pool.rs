//! Database connection helpers.

use sea_orm::{Database, DatabaseConnection, DbErr};

/// Connect to a PostgreSQL database from a `postgres://...` URL.
pub async fn connect(database_url: &str) -> Result<DatabaseConnection, DbErr> {
    Database::connect(database_url).await
}
