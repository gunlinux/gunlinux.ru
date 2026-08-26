//! Concrete SeaORM-backed implementations of the `domain` repository traits.
//!
//! Each repository owns a `DatabaseConnection` and maps SeaORM driver errors
//! into `domain::RepoError` so layers above never see driver types.

mod category_repository;
mod icon_repository;
mod post_repository;
mod tag_repository;
mod user_repository;
mod visit_repository;

pub use category_repository::CategoryRepository;
pub use icon_repository::IconRepository;
pub use post_repository::PostRepository;
pub use tag_repository::TagRepository;
pub use user_repository::UserRepository;
pub use visit_repository::VisitRepository;

use domain::RepoError;
use sea_orm::DbErr;
use sea_orm::SqlErr;

/// Translate a SeaORM error into the domain `RepoError`.
///
/// Unique-constraint violations become `RepoError::Conflict` (duplicate
/// alias/title surfaces as an integrity error). Everything else becomes
/// `RepoError::Db`.
pub(crate) fn translate_err(err: DbErr) -> RepoError {
    if let Some(SqlErr::UniqueConstraintViolation(message)) = err.sql_err() {
        return RepoError::Conflict(message);
    }
    RepoError::Db(err.to_string())
}
