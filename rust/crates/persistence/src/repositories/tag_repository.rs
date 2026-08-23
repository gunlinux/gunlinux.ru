//! `TagRepository` — ports `app/repositories/tag.py`.

use async_trait::async_trait;
use sea_orm::sea_query::JoinType;
use sea_orm::{
    ActiveModelTrait, ColumnTrait, DatabaseConnection, EntityTrait, QueryFilter, QuerySelect,
    RelationTrait, Set,
};

use domain::repositories::{Repository, TagRepository as TagRepoTrait};
use domain::{RepoError, Tag};

use super::translate_err;
use crate::entities::tag;

/// SeaORM-backed `TagRepository`.
pub struct TagRepository {
    db: DatabaseConnection,
}

impl TagRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }
}

/// Map a tag row to the domain `Tag` — Python: `title=t.title or "",
/// alias=t.alias or ""`.
pub(crate) fn to_domain(t: tag::Model) -> Tag {
    Tag {
        id: Some(t.id),
        title: t.title.unwrap_or_default(),
        alias: t.alias.unwrap_or_default(),
    }
}

#[async_trait]
impl Repository<Tag, i32> for TagRepository {
    async fn get_by_id(&self, id: i32) -> Result<Option<Tag>, RepoError> {
        let row = tag::Entity::find_by_id(id)
            .one(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(row.map(to_domain))
    }

    async fn get_all(&self) -> Result<Vec<Tag>, RepoError> {
        let rows = tag::Entity::find()
            .all(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(rows.into_iter().map(to_domain).collect())
    }

    async fn create(&self, entity: &Tag) -> Result<Tag, RepoError> {
        let active = tag::ActiveModel {
            title: Set(Some(entity.title.clone())),
            alias: Set(Some(entity.alias.clone())),
            ..Default::default()
        };
        let result = active.insert(&self.db).await.map_err(translate_err)?;
        let mut created = entity.clone();
        created.id = Some(result.id);
        Ok(created)
    }

    async fn update(&self, entity: &Tag) -> Result<Tag, RepoError> {
        let id = match entity.id {
            Some(id) => id,
            None => return Err(RepoError::NotFound),
        };
        let existing = tag::Entity::find_by_id(id)
            .one(&self.db)
            .await
            .map_err(translate_err)?;
        let mut active: tag::ActiveModel = match existing {
            Some(model) => model.into(),
            None => return Err(RepoError::NotFound),
        };
        active.title = Set(Some(entity.title.clone()));
        active.alias = Set(Some(entity.alias.clone()));
        active.update(&self.db).await.map_err(translate_err)?;
        let mut updated = entity.clone();
        updated.id = Some(id);
        Ok(updated)
    }

    async fn delete(&self, id: i32) -> Result<bool, RepoError> {
        let result = tag::Entity::delete_by_id(id)
            .exec(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(result.rows_affected > 0)
    }
}

#[async_trait]
impl TagRepoTrait for TagRepository {
    async fn get_by_alias(&self, alias: &str) -> Result<Option<Tag>, RepoError> {
        let row = tag::Entity::find()
            .filter(tag::Column::Alias.eq(alias))
            .one(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(row.map(to_domain))
    }

    async fn get_tags_for_post(&self, post_id: i32) -> Result<Vec<Tag>, RepoError> {
        use crate::entities::{post, posts_tag};
        let rows = tag::Entity::find()
            .join(JoinType::InnerJoin, tag::Relation::PostsTags.def())
            .join(JoinType::InnerJoin, posts_tag::Relation::Post.def())
            .filter(post::Column::Id.eq(post_id))
            .all(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(rows.into_iter().map(to_domain).collect())
    }
}
