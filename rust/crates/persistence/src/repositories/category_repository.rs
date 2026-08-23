//! `CategoryRepository` — ports `app/repositories/category.py`.

use async_trait::async_trait;
use sea_orm::{ActiveModelTrait, ColumnTrait, DatabaseConnection, EntityTrait, QueryFilter, Set};

use domain::repositories::{CategoryRepository as CategoryRepoTrait, Repository};
use domain::{Category, RepoError};

use super::translate_err;
use crate::entities::category;

/// SeaORM-backed `CategoryRepository`.
pub struct CategoryRepository {
    db: DatabaseConnection,
}

impl CategoryRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }
}

/// Map a category row to the domain `Category` — Python: `title or ""`,
/// `alias or ""`; `template`/`page` pass through as-is.
pub(crate) fn to_domain(c: category::Model) -> Category {
    Category {
        id: Some(c.id),
        title: c.title.unwrap_or_default(),
        alias: c.alias.unwrap_or_default(),
        template: c.template,
        page: c.page,
    }
}

#[async_trait]
impl Repository<Category, i32> for CategoryRepository {
    async fn get_by_id(&self, id: i32) -> Result<Option<Category>, RepoError> {
        let row = category::Entity::find_by_id(id)
            .one(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(row.map(to_domain))
    }

    async fn get_all(&self) -> Result<Vec<Category>, RepoError> {
        let rows = category::Entity::find()
            .all(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(rows.into_iter().map(to_domain).collect())
    }

    async fn create(&self, entity: &Category) -> Result<Category, RepoError> {
        let mut active = category::ActiveModel {
            title: Set(Some(entity.title.clone())),
            alias: Set(Some(entity.alias.clone())),
            page: Set(entity.page),
            ..Default::default()
        };
        if let Some(template) = &entity.template {
            active.template = Set(Some(template.clone()));
        }
        let result = active.insert(&self.db).await.map_err(translate_err)?;
        let mut created = entity.clone();
        created.id = Some(result.id);
        Ok(created)
    }

    async fn update(&self, entity: &Category) -> Result<Category, RepoError> {
        let id = match entity.id {
            Some(id) => id,
            None => return Err(RepoError::NotFound),
        };
        let existing = category::Entity::find_by_id(id)
            .one(&self.db)
            .await
            .map_err(translate_err)?;
        let mut active: category::ActiveModel = match existing {
            Some(model) => model.into(),
            None => return Err(RepoError::NotFound),
        };
        active.title = Set(Some(entity.title.clone()));
        active.alias = Set(Some(entity.alias.clone()));
        // Python update does not touch `page`; only template is updated when
        // present. Keep that behavior.
        if let Some(template) = &entity.template {
            active.template = Set(Some(template.clone()));
        }
        active.update(&self.db).await.map_err(translate_err)?;
        let mut updated = entity.clone();
        updated.id = Some(id);
        Ok(updated)
    }

    async fn delete(&self, id: i32) -> Result<bool, RepoError> {
        let result = category::Entity::delete_by_id(id)
            .exec(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(result.rows_affected > 0)
    }
}

#[async_trait]
impl CategoryRepoTrait for CategoryRepository {
    async fn get_by_alias(&self, alias: &str) -> Result<Option<Category>, RepoError> {
        let row = category::Entity::find()
            .filter(category::Column::Alias.eq(alias))
            .one(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(row.map(to_domain))
    }
}
