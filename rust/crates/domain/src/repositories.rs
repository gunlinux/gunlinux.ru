//! Repository traits — the port seam between persistence and the rest of the
//! app (mirrors `app/repositories/base.py` + the per-model finders).
//!
//! `persistence` implements these for real databases; `web` depends only on the
//! traits (via `Arc<dyn ...>`) so routes, services and the admin panel are
//! database-platform independent. Tests inject in-memory fakes.

use async_trait::async_trait;

use crate::error::RepoError;
use crate::{Category, Icon, Post, Tag, User};

/// Generic CRUD port for any entity.
#[async_trait]
pub trait Repository<T, Id>: Send + Sync {
    async fn get_by_id(&self, id: Id) -> Result<Option<T>, RepoError>;
    async fn get_all(&self) -> Result<Vec<T>, RepoError>;
    async fn create(&self, entity: &T) -> Result<T, RepoError>;
    async fn update(&self, entity: &T) -> Result<T, RepoError>;
    async fn delete(&self, id: Id) -> Result<bool, RepoError>;
}

#[async_trait]
pub trait PostRepository: Repository<Post, i32> {
    async fn get_by_alias(&self, alias: &str) -> Result<Option<Post>, RepoError>;
    async fn get_published_posts(&self) -> Result<Vec<Post>, RepoError>;
    async fn get_all_published_content(&self) -> Result<Vec<Post>, RepoError>;
    async fn get_page_posts(&self) -> Result<Vec<Post>, RepoError>;
    async fn get_posts_by_tag(&self, tag_id: i32) -> Result<Vec<Post>, RepoError>;
    async fn get_tags_for_post(&self, post_id: i32) -> Result<Vec<Tag>, RepoError>;
}

#[async_trait]
pub trait TagRepository: Repository<Tag, i32> {
    async fn get_by_alias(&self, alias: &str) -> Result<Option<Tag>, RepoError>;
    async fn get_tags_for_post(&self, post_id: i32) -> Result<Vec<Tag>, RepoError>;
}

#[async_trait]
pub trait UserRepository: Repository<User, i32> {
    async fn get_by_name(&self, name: &str) -> Result<Option<User>, RepoError>;
    async fn authenticate(&self, name: &str, password: &str) -> Result<Option<User>, RepoError>;
}

#[async_trait]
pub trait CategoryRepository: Repository<Category, i32> {
    async fn get_by_alias(&self, alias: &str) -> Result<Option<Category>, RepoError>;
}

#[async_trait]
pub trait IconRepository: Repository<Icon, i32> {
    async fn get_by_title(&self, title: &str) -> Result<Option<Icon>, RepoError>;
}
