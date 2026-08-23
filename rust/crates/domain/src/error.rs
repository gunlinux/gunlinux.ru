use thiserror::Error;

/// Errors crossing the repository boundary. Persistence crates map their own
/// driver errors into this type so layers above never see driver types.
#[derive(Debug, Error, Clone, PartialEq)]
pub enum RepoError {
    #[error("entity not found")]
    NotFound,
    #[error("conflict: {0}")]
    Conflict(String),
    #[error("database error: {0}")]
    Db(String),
}
