//! `IconRepository` — SeaORM-backed icon storage.

use async_trait::async_trait;
use sea_orm::{ActiveModelTrait, ColumnTrait, DatabaseConnection, EntityTrait, QueryFilter, Set};

use domain::repositories::{IconRepository as IconRepoTrait, Repository};
use domain::{Icon, RepoError};

use super::translate_err;
use crate::entities::icon;

/// SeaORM-backed `IconRepository`.
pub struct IconRepository {
    db: DatabaseConnection,
}

impl IconRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }
}

/// Map an icon row to the domain `Icon` — all fields pass through
/// unchanged.
pub(crate) fn to_domain(i: icon::Model) -> Icon {
    Icon {
        id: Some(i.id),
        title: i.title,
        url: i.url,
        content: i.content,
    }
}

#[async_trait]
impl Repository<Icon, i32> for IconRepository {
    async fn get_by_id(&self, id: i32) -> Result<Option<Icon>, RepoError> {
        let row = icon::Entity::find_by_id(id)
            .one(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(row.map(to_domain))
    }

    async fn get_all(&self) -> Result<Vec<Icon>, RepoError> {
        let rows = icon::Entity::find()
            .all(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(rows.into_iter().map(to_domain).collect())
    }

    async fn create(&self, entity: &Icon) -> Result<Icon, RepoError> {
        let mut active = icon::ActiveModel {
            title: Set(entity.title.clone()),
            url: Set(entity.url.clone()),
            ..Default::default()
        };
        if let Some(content) = &entity.content {
            active.content = Set(Some(content.clone()));
        }
        let result = active.insert(&self.db).await.map_err(translate_err)?;
        let mut created = entity.clone();
        created.id = Some(result.id);
        Ok(created)
    }

    async fn update(&self, entity: &Icon) -> Result<Icon, RepoError> {
        let id = match entity.id {
            Some(id) => id,
            None => return Err(RepoError::NotFound),
        };
        let existing = icon::Entity::find_by_id(id)
            .one(&self.db)
            .await
            .map_err(translate_err)?;
        let mut active: icon::ActiveModel = match existing {
            Some(model) => model.into(),
            None => return Err(RepoError::NotFound),
        };
        active.title = Set(entity.title.clone());
        active.url = Set(entity.url.clone());
        if let Some(content) = &entity.content {
            active.content = Set(Some(content.clone()));
        }
        active.update(&self.db).await.map_err(translate_err)?;
        let mut updated = entity.clone();
        updated.id = Some(id);
        Ok(updated)
    }

    async fn delete(&self, id: i32) -> Result<bool, RepoError> {
        let result = icon::Entity::delete_by_id(id)
            .exec(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(result.rows_affected > 0)
    }
}

#[async_trait]
impl IconRepoTrait for IconRepository {
    async fn get_by_title(&self, title: &str) -> Result<Option<Icon>, RepoError> {
        let row = icon::Entity::find()
            .filter(icon::Column::Title.eq(title))
            .one(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(row.map(to_domain))
    }
}
