//! `PostRepository` — ports `app/repositories/post.py`.

use async_trait::async_trait;
use sea_orm::sea_query::{Expr, JoinType};
use sea_orm::{
    ActiveModelTrait, ColumnTrait, DatabaseConnection, EntityTrait, QueryFilter, QueryOrder,
    QuerySelect, RelationTrait, Set,
};

use domain::repositories::{PostRepository as PostRepoTrait, Repository};
use domain::{Post, RepoError, Tag};

use super::translate_err;
use crate::entities::{category, post, posts_tag, tag};
use crate::repositories::tag_repository;

/// SeaORM-backed `PostRepository`.
pub struct PostRepository {
    db: DatabaseConnection,
}

impl PostRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }
}

/// Map a post row to the domain `Post`, mirroring the Python `_to_domain`:
/// strings default to `""` when NULL, and `is_page` is derived from the
/// loaded category (`bool(category.page)` when `category_id` is set).
pub(crate) fn to_domain(post: post::Model, category: Option<category::Model>) -> Post {
    Post {
        id: Some(post.id),
        pagetitle: post.pagetitle,
        alias: post.alias,
        content: post.content.unwrap_or_default(),
        createdon: post.createdon,
        publishedon: post.publishedon,
        category_id: post.category_id,
        is_page: post.category_id.is_some()
            && category.as_ref().and_then(|c| c.page).unwrap_or(false),
        user_id: post.user_id,
    }
}

#[async_trait]
impl Repository<Post, i32> for PostRepository {
    async fn get_by_id(&self, id: i32) -> Result<Option<Post>, RepoError> {
        let row = post::Entity::find_by_id(id)
            .find_also_related(category::Entity)
            .one(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(row.map(|(p, c)| to_domain(p, c)))
    }

    async fn get_all(&self) -> Result<Vec<Post>, RepoError> {
        let rows = post::Entity::find()
            .find_also_related(category::Entity)
            .all(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(rows.into_iter().map(|(p, c)| to_domain(p, c)).collect())
    }

    async fn create(&self, entity: &Post) -> Result<Post, RepoError> {
        let mut active = post::ActiveModel {
            pagetitle: Set(entity.pagetitle.clone()),
            alias: Set(entity.alias.clone()),
            content: Set(Some(entity.content.clone())),
            ..Default::default()
        };
        // Python only sets optional fields when present, so a None value is
        // left as NULL rather than overwriting existing data.
        if let Some(createdon) = entity.createdon {
            active.createdon = Set(Some(createdon));
        }
        if let Some(publishedon) = entity.publishedon {
            active.publishedon = Set(Some(publishedon));
        }
        if let Some(category_id) = entity.category_id {
            active.category_id = Set(Some(category_id));
        }
        if let Some(user_id) = entity.user_id {
            active.user_id = Set(Some(user_id));
        }
        let result = active.insert(&self.db).await.map_err(translate_err)?;
        let mut created = entity.clone();
        created.id = Some(result.id);
        Ok(created)
    }

    async fn update(&self, entity: &Post) -> Result<Post, RepoError> {
        let id = match entity.id {
            Some(id) => id,
            None => return Err(RepoError::NotFound),
        };
        let existing = post::Entity::find_by_id(id)
            .one(&self.db)
            .await
            .map_err(translate_err)?;
        let mut active: post::ActiveModel = match existing {
            Some(model) => model.into(),
            None => return Err(RepoError::NotFound),
        };
        active.pagetitle = Set(entity.pagetitle.clone());
        active.alias = Set(entity.alias.clone());
        active.content = Set(Some(entity.content.clone()));
        if let Some(createdon) = entity.createdon {
            active.createdon = Set(Some(createdon));
        }
        if let Some(publishedon) = entity.publishedon {
            active.publishedon = Set(Some(publishedon));
        }
        if let Some(category_id) = entity.category_id {
            active.category_id = Set(Some(category_id));
        }
        if let Some(user_id) = entity.user_id {
            active.user_id = Set(Some(user_id));
        }
        active.update(&self.db).await.map_err(translate_err)?;
        let mut updated = entity.clone();
        updated.id = Some(id);
        Ok(updated)
    }

    /// The Python `delete` raises `ValueError` when the post is missing, but
    /// the generic trait contract returns `Result<bool, RepoError>` — follow
    /// the trait: `Ok(true)` if a row was deleted, `Ok(false)` otherwise.
    async fn delete(&self, id: i32) -> Result<bool, RepoError> {
        let result = post::Entity::delete_by_id(id)
            .exec(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(result.rows_affected > 0)
    }
}

#[async_trait]
impl PostRepoTrait for PostRepository {
    async fn get_by_alias(&self, alias: &str) -> Result<Option<Post>, RepoError> {
        let row = post::Entity::find()
            .filter(post::Column::Alias.eq(alias))
            .find_also_related(category::Entity)
            .one(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(row.map(|(p, c)| to_domain(p, c)))
    }

    /// `publishedon IS NOT NULL AND category_id IS NULL`, ordered by
    /// `publishedon` DESC. All returned posts have `category_id = NULL`, so
    /// `is_page` is always false — equivalent to the Python query loading the
    /// (necessarily absent) category.
    async fn get_published_posts(&self) -> Result<Vec<Post>, RepoError> {
        let rows = post::Entity::find()
            .filter(post::Column::Publishedon.is_not_null())
            .filter(post::Column::CategoryId.is_null())
            .order_by_desc(post::Column::Publishedon)
            .all(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(rows.into_iter().map(|p| to_domain(p, None)).collect())
    }

    /// `publishedon IS NOT NULL AND category.page IS NOT TRUE` (left-joined
    /// categories), ordered by `publishedon` DESC. The `page IS NOT TRUE`
    /// predicate (null-safe: `NULL IS NOT TRUE` is true, so uncategorised
    /// posts are included) guarantees every returned post has `is_page ==
    /// false`, matching the Python `_to_domain` with the loaded category.
    async fn get_all_published_content(&self) -> Result<Vec<Post>, RepoError> {
        let rows = post::Entity::find()
            .join(JoinType::LeftJoin, post::Relation::Category.def())
            .filter(post::Column::Publishedon.is_not_null())
            .filter(Expr::col(category::Column::Page).is_not(true))
            .order_by_desc(post::Column::Publishedon)
            .all(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(rows.into_iter().map(|p| to_domain(p, None)).collect())
    }

    /// Inner-joins categories where `page IS TRUE`. The join guarantees the
    /// category exists and the filter guarantees `is_page == true`, matching
    /// the Python `_to_domain` (`bool(category.page)`).
    async fn get_page_posts(&self) -> Result<Vec<Post>, RepoError> {
        let rows = post::Entity::find()
            .join(JoinType::InnerJoin, post::Relation::Category.def())
            .filter(Expr::col(category::Column::Page).eq(true))
            .all(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(rows
            .into_iter()
            .map(|p| {
                let mut post = to_domain(p, None);
                post.is_page = true;
                post
            })
            .collect())
    }

    /// Posts linked to the given tag via `posts_tags`, with category loaded.
    async fn get_posts_by_tag(&self, tag_id: i32) -> Result<Vec<Post>, RepoError> {
        let rows = post::Entity::find()
            .join(JoinType::InnerJoin, post::Relation::PostsTags.def())
            .join(JoinType::InnerJoin, posts_tag::Relation::Tag.def())
            .filter(tag::Column::Id.eq(tag_id))
            .find_also_related(category::Entity)
            .all(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(rows.into_iter().map(|(p, c)| to_domain(p, c)).collect())
    }

    /// Tags linked to the given post via `posts_tags`.
    async fn get_tags_for_post(&self, post_id: i32) -> Result<Vec<Tag>, RepoError> {
        let rows = tag::Entity::find()
            .join(JoinType::InnerJoin, tag::Relation::PostsTags.def())
            .join(JoinType::InnerJoin, posts_tag::Relation::Post.def())
            .filter(post::Column::Id.eq(post_id))
            .all(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(rows.into_iter().map(tag_repository::to_domain).collect())
    }
}
