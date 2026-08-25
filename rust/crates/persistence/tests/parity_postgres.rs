//! Postgres parity suite (plan.md §3 Thread A) — the exact same repository
//! test bodies as `repositories.rs`, run against a real PostgreSQL 16.
//!
//! Postgres is resolved from `TEST_DATABASE_URL` when set (CI service
//! container), otherwise via a `postgres:16` testcontainer. Every test gets a
//! fresh scratch database with the baseline migration applied by the real
//! `Migrator`, so this suite also verifies
//! `m20260101_000001_create_schema` is Postgres-correct.
//!
//! Gated on the `postgres-parity` feature: default `cargo test` stays
//! SQLite-only and container-free.

#![cfg(feature = "postgres-parity")]

mod common;

use common::suite;

#[tokio::test]
async fn test_post_crud() {
    let test_db = common::postgres::provision().await;
    suite::post_crud(&test_db.db).await;
    common::postgres::cleanup(test_db).await;
}

#[tokio::test]
async fn test_post_update_not_found_is_notfound() {
    let test_db = common::postgres::provision().await;
    suite::post_update_not_found_is_notfound(&test_db.db).await;
    common::postgres::cleanup(test_db).await;
}

#[tokio::test]
async fn test_post_duplicate_alias_is_conflict() {
    let test_db = common::postgres::provision().await;
    suite::post_duplicate_alias_is_conflict(&test_db.db).await;
    common::postgres::cleanup(test_db).await;
}

#[tokio::test]
async fn test_post_published() {
    let test_db = common::postgres::provision().await;
    suite::post_published(&test_db.db).await;
    common::postgres::cleanup(test_db).await;
}

#[tokio::test]
async fn test_post_tag_relations_and_page_queries() {
    let test_db = common::postgres::provision().await;
    suite::post_tag_relations_and_page_queries(&test_db.db).await;
    common::postgres::cleanup(test_db).await;
}

#[tokio::test]
async fn test_tag_crud() {
    let test_db = common::postgres::provision().await;
    suite::tag_crud(&test_db.db).await;
    common::postgres::cleanup(test_db).await;
}

#[tokio::test]
async fn test_user_crud() {
    let test_db = common::postgres::provision().await;
    suite::user_crud(&test_db.db).await;
    common::postgres::cleanup(test_db).await;
}

#[tokio::test]
async fn test_user_authenticate() {
    let test_db = common::postgres::provision().await;
    suite::user_authenticate(&test_db.db).await;
    common::postgres::cleanup(test_db).await;
}

#[tokio::test]
async fn test_category_crud() {
    let test_db = common::postgres::provision().await;
    suite::category_crud(&test_db.db).await;
    common::postgres::cleanup(test_db).await;
}

#[tokio::test]
async fn test_icon_crud() {
    let test_db = common::postgres::provision().await;
    suite::icon_crud(&test_db.db).await;
    common::postgres::cleanup(test_db).await;
}

#[tokio::test]
async fn test_visit_repo() {
    let test_db = common::postgres::provision().await;
    suite::visit_repo(&test_db.db).await;
    common::postgres::cleanup(test_db).await;
}
