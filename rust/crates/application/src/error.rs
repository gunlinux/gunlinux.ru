//! Application-layer error: the outcome of a use case, independent of any
//! HTTP or driver concern. `web` maps it onto its own `WebError`/status
//! codes; `RepoError` (the port's error) is translated here so no driver
//! error type leaks above the repository line.

use domain::RepoError;
use thiserror::Error;

/// Outcome of a use case.
#[derive(Debug, Error)]
pub enum AppError {
    #[error("not found")]
    NotFound,
    #[error("conflict: {0}")]
    Conflict(String),
    #[error("internal error: {0}")]
    Internal(String),
}

impl From<RepoError> for AppError {
    fn from(e: RepoError) -> Self {
        match e {
            RepoError::NotFound => AppError::NotFound,
            RepoError::Conflict(msg) => AppError::Conflict(msg),
            RepoError::Db(msg) => AppError::Internal(msg),
        }
    }
}
