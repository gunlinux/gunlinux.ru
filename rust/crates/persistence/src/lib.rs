//! Persistence layer: SeaORM entities, migrations, pools, and implementations
//! of the `domain` repository traits for PostgreSQL.

pub mod entities;
pub mod migrator;
pub mod pool;
pub mod repositories;
