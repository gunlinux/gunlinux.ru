//! Shared repository test harness (plan.md §3 Thread A — platform-independent
//! tests).
//!
//! The suite bodies live in [`suite`] and take a `&DatabaseConnection`.
//! [`postgres::provision`] creates a fresh scratch PostgreSQL database per
//! test with the baseline migration applied; the exact same assertions run
//! against every scratch DB.

pub mod suite;

#[allow(dead_code)]
pub mod postgres;
