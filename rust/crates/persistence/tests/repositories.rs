//! Port of `tests/test_repositories.py` — repository CRUD/finder tests run
//! against a temp-file SQLite database with the baseline migration applied.
//!
//! The test bodies live in `common::suite`; this file only wires them to a
//! SQLite database (default, fast, CI). The same bodies run against real
//! PostgreSQL in `parity_postgres.rs` (feature `postgres-parity`).

mod common;

use common::suite;

#[tokio::test]
async fn test_post_crud() {
    let (db, _file) = common::sqlite_db().await;
    suite::post_crud(&db).await;
}

#[tokio::test]
async fn test_post_update_not_found_is_notfound() {
    let (db, _file) = common::sqlite_db().await;
    suite::post_update_not_found_is_notfound(&db).await;
}

#[tokio::test]
async fn test_post_duplicate_alias_is_conflict() {
    let (db, _file) = common::sqlite_db().await;
    suite::post_duplicate_alias_is_conflict(&db).await;
}

#[tokio::test]
async fn test_post_published() {
    let (db, _file) = common::sqlite_db().await;
    suite::post_published(&db).await;
}

#[tokio::test]
async fn test_post_tag_relations_and_page_queries() {
    let (db, _file) = common::sqlite_db().await;
    suite::post_tag_relations_and_page_queries(&db).await;
}

#[tokio::test]
async fn test_tag_crud() {
    let (db, _file) = common::sqlite_db().await;
    suite::tag_crud(&db).await;
}

#[tokio::test]
async fn test_user_crud() {
    let (db, _file) = common::sqlite_db().await;
    suite::user_crud(&db).await;
}

#[tokio::test]
async fn test_user_authenticate() {
    let (db, _file) = common::sqlite_db().await;
    suite::user_authenticate(&db).await;
}

#[tokio::test]
async fn test_category_crud() {
    let (db, _file) = common::sqlite_db().await;
    suite::category_crud(&db).await;
}

#[tokio::test]
async fn test_icon_crud() {
    let (db, _file) = common::sqlite_db().await;
    suite::icon_crud(&db).await;
}
