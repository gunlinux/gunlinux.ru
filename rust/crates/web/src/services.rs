//! Service layer — thin structs over the domain repository traits, mirroring
//! `app/services/*.py` method-for-method.

use std::sync::Arc;

use chrono::{DateTime, Utc};
use domain::{
    Category, CategoryRepository, Icon, IconRepository, Post, PostRepository, RepoError, Tag,
    TagRepository, User, UserRepository,
};
use thiserror::Error;

/// Error type shared by services and routes. Maps to HTTP status codes in
/// [`crate::routes`].
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

impl From<minijinja::Error> for WebError {
    fn from(e: minijinja::Error) -> Self {
        WebError::Internal(e.to_string())
    }
}

pub struct PostService {
    pub repo: Arc<dyn PostRepository>,
}

impl PostService {
    pub fn new(repo: Arc<dyn PostRepository>) -> Self {
        Self { repo }
    }

    pub async fn get_post_by_alias(&self, alias: &str) -> Result<Option<Post>, WebError> {
        Ok(self.repo.get_by_alias(alias).await?)
    }

    pub async fn get_all_posts(&self) -> Result<Vec<Post>, WebError> {
        Ok(self.repo.get_all().await?)
    }

    pub async fn get_published_posts(&self) -> Result<Vec<Post>, WebError> {
        Ok(self.repo.get_published_posts().await?)
    }

    pub async fn get_all_published_content(&self) -> Result<Vec<Post>, WebError> {
        Ok(self.repo.get_all_published_content().await?)
    }

    pub async fn get_page_posts(&self) -> Result<Vec<Post>, WebError> {
        Ok(self.repo.get_page_posts().await?)
    }

    pub async fn get_posts_by_tag(&self, tag_id: i32) -> Result<Vec<Post>, WebError> {
        Ok(self.repo.get_posts_by_tag(tag_id).await?)
    }

    pub async fn get_tags_for_post(&self, post_id: i32) -> Result<Vec<Tag>, WebError> {
        Ok(self.repo.get_tags_for_post(post_id).await?)
    }

    /// Content version for the response cache (see `PostRepository::latest_update`).
    pub async fn latest_update(&self) -> Result<Option<DateTime<Utc>>, WebError> {
        Ok(self.repo.latest_update().await?)
    }

    pub async fn create_post(&self, post: &Post) -> Result<Post, WebError> {
        Ok(self.repo.create(post).await?)
    }
}

pub struct TagService {
    pub repo: Arc<dyn TagRepository>,
}

impl TagService {
    pub fn new(repo: Arc<dyn TagRepository>) -> Self {
        Self { repo }
    }

    pub async fn get_tag_by_alias(&self, alias: &str) -> Result<Option<Tag>, WebError> {
        Ok(self.repo.get_by_alias(alias).await?)
    }

    pub async fn get_all_tags(&self) -> Result<Vec<Tag>, WebError> {
        Ok(self.repo.get_all().await?)
    }

    pub async fn create_tag(&self, tag: &Tag) -> Result<Tag, WebError> {
        Ok(self.repo.create(tag).await?)
    }
}

pub struct UserService {
    pub repo: Arc<dyn UserRepository>,
}

impl UserService {
    pub fn new(repo: Arc<dyn UserRepository>) -> Self {
        Self { repo }
    }

    pub async fn authenticate_user(
        &self,
        name: &str,
        password: &str,
    ) -> Result<Option<User>, WebError> {
        Ok(self.repo.authenticate(name, password).await?)
    }

    pub async fn create_user(&self, user: &User) -> Result<User, WebError> {
        Ok(self.repo.create(user).await?)
    }
}

pub struct CategoryService {
    pub repo: Arc<dyn CategoryRepository>,
}

impl CategoryService {
    pub fn new(repo: Arc<dyn CategoryRepository>) -> Self {
        Self { repo }
    }

    pub async fn get_category_by_alias(&self, alias: &str) -> Result<Option<Category>, WebError> {
        Ok(self.repo.get_by_alias(alias).await?)
    }

    pub async fn create_category(&self, category: &Category) -> Result<Category, WebError> {
        Ok(self.repo.create(category).await?)
    }
}

pub struct IconService {
    pub repo: Arc<dyn IconRepository>,
}

impl IconService {
    pub fn new(repo: Arc<dyn IconRepository>) -> Self {
        Self { repo }
    }

    pub async fn get_icon_by_title(&self, title: &str) -> Result<Option<Icon>, WebError> {
        Ok(self.repo.get_by_title(title).await?)
    }

    pub async fn get_all_icons(&self) -> Result<Vec<Icon>, WebError> {
        Ok(self.repo.get_all().await?)
    }

    pub async fn create_icon(&self, icon: &Icon) -> Result<Icon, WebError> {
        Ok(self.repo.create(icon).await?)
    }
}
