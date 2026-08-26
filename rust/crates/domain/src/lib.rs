//! Domain layer: pure types, pure logic and the repository traits that are the
//! seam between persistence and the rest of the app. No I/O here.
//!
//! This crate is the frozen contract for the Rust rewrite. Other crates
//! (`persistence`, `web`) depend on it; do not change public APIs casually.

pub mod category;
pub mod error;
pub mod icon;
pub mod post;
pub mod repositories;
pub mod security;
pub mod tag;
pub mod user;
pub mod visit;

pub use category::Category;
pub use error::RepoError;
pub use icon::Icon;
pub use post::{group_posts_by_year, render_markdown, Post, YearGroup};
pub use repositories::{
    CategoryRepository, IconRepository, PostRepository, Repository, TagRepository, UserRepository,
};
pub use tag::Tag;
pub use user::User;
pub use visit::{DailyCount, PathCount, SourceCount, Visit, VisitRepository};
