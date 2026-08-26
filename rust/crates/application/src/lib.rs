//! Application layer: use cases (interactors) over the domain repository
//! ports.
//!
//! Depends only on `domain` — no HTTP types, no drivers, no templates. Each
//! use case takes repository trait objects and plain inputs and returns
//! domain results or an [`AppError`], so the rules are exercisable without an
//! axum `Router` (the `web` crate translates between HTTP and these
//! functions).

pub mod admin;
pub mod error;
pub mod posts;

pub use error::AppError;
