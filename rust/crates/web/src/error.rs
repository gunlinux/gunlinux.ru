//! HTTP-flavored error type for the web layer.
//!
//! Use cases in the `application` crate return [`AppError`]; this type adds
//! the HTTP response mapping (via [`crate::routes`]) plus translations from
//! the port error (`RepoError`) and the template engine.

use application::AppError;
use domain::RepoError;
use thiserror::Error;

/// Error type used by route handlers and the admin panel. Maps to HTTP status
/// codes in [`crate::routes`].
#[derive(Debug, Error)]
pub enum WebError {
    #[error("not found")]
    NotFound,
    #[error("conflict: {0}")]
    Conflict(String),
    #[error("internal error: {0}")]
    Internal(String),
}

impl From<RepoError> for WebError {
    fn from(e: RepoError) -> Self {
        match e {
            RepoError::NotFound => WebError::NotFound,
            RepoError::Conflict(msg) => WebError::Conflict(msg),
            RepoError::Db(msg) => WebError::Internal(msg),
        }
    }
}

impl From<AppError> for WebError {
    fn from(e: AppError) -> Self {
        match e {
            AppError::NotFound => WebError::NotFound,
            AppError::Conflict(msg) => WebError::Conflict(msg),
            AppError::Internal(msg) => WebError::Internal(msg),
        }
    }
}

impl From<minijinja::Error> for WebError {
    fn from(e: minijinja::Error) -> Self {
        WebError::Internal(e.to_string())
    }
}
