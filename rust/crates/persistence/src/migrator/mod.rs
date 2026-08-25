//! SeaORM migrations.
//!
//! A single baseline migration reproduces the schema from
//! `app/infrastructure/database.py` (the post-16-Alembic-migrations state).
//! Production cutover stamps this migration on the existing DB rather than
//! re-running it.

mod m20260101_000001_create_schema;
mod m20260825_000002_add_post_update_date;

use sea_orm_migration::prelude::*;

// Re-exported so tests and the server binary can run migrations without
// depending on `sea-orm-migration` directly.
pub use sea_orm_migration::MigratorTrait;

/// The `Migrator` for this application.
pub struct Migrator;

#[async_trait::async_trait]
impl MigratorTrait for Migrator {
    fn migrations() -> Vec<Box<dyn MigrationTrait>> {
        vec![
            Box::new(m20260101_000001_create_schema::Migration),
            Box::new(m20260825_000002_add_post_update_date::Migration),
        ]
    }
}
