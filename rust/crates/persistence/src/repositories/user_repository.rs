//! `UserRepository` — ports `app/repositories/user.py`.

use async_trait::async_trait;
use sea_orm::{ActiveModelTrait, ColumnTrait, DatabaseConnection, EntityTrait, QueryFilter, Set};

use domain::repositories::{Repository, UserRepository as UserRepoTrait};
use domain::{RepoError, User};

use super::translate_err;
use crate::entities::user;

/// SeaORM-backed `UserRepository`.
pub struct UserRepository {
    db: DatabaseConnection,
}

impl UserRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }
}

/// Map a user row to the domain `User`. Python: `name or ""`, `password or
/// ""`, and `bool(authenticated) if authenticated is not None else False`.
pub(crate) fn to_domain(u: user::Model) -> User {
    User {
        id: Some(u.id),
        name: u.name,
        password: u.password.unwrap_or_default(),
        authenticated: u.authenticated.unwrap_or(false),
        createdon: u.createdon,
    }
}

#[async_trait]
impl Repository<User, i32> for UserRepository {
    async fn get_by_id(&self, id: i32) -> Result<Option<User>, RepoError> {
        let row = user::Entity::find_by_id(id)
            .one(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(row.map(to_domain))
    }

    async fn get_all(&self) -> Result<Vec<User>, RepoError> {
        let rows = user::Entity::find()
            .all(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(rows.into_iter().map(to_domain).collect())
    }

    async fn create(&self, entity: &User) -> Result<User, RepoError> {
        let mut active = user::ActiveModel {
            name: Set(entity.name.clone()),
            password: Set(Some(entity.password.clone())),
            authenticated: Set(Some(entity.authenticated)),
            ..Default::default()
        };
        if let Some(createdon) = entity.createdon {
            active.createdon = Set(Some(createdon));
        }
        let result = active.insert(&self.db).await.map_err(translate_err)?;
        let mut created = entity.clone();
        created.id = Some(result.id);
        Ok(created)
    }

    async fn update(&self, entity: &User) -> Result<User, RepoError> {
        let id = match entity.id {
            Some(id) => id,
            None => return Err(RepoError::NotFound),
        };
        let existing = user::Entity::find_by_id(id)
            .one(&self.db)
            .await
            .map_err(translate_err)?;
        let mut active: user::ActiveModel = match existing {
            Some(model) => model.into(),
            None => return Err(RepoError::NotFound),
        };
        active.name = Set(entity.name.clone());
        active.password = Set(Some(entity.password.clone()));
        active.authenticated = Set(Some(entity.authenticated));
        if let Some(createdon) = entity.createdon {
            active.createdon = Set(Some(createdon));
        }
        active.update(&self.db).await.map_err(translate_err)?;
        let mut updated = entity.clone();
        updated.id = Some(id);
        Ok(updated)
    }

    async fn delete(&self, id: i32) -> Result<bool, RepoError> {
        let result = user::Entity::delete_by_id(id)
            .exec(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(result.rows_affected > 0)
    }
}

#[async_trait]
impl UserRepoTrait for UserRepository {
    async fn get_by_name(&self, name: &str) -> Result<Option<User>, RepoError> {
        let row = user::Entity::find()
            .filter(user::Column::Name.eq(name))
            .one(&self.db)
            .await
            .map_err(translate_err)?;
        Ok(row.map(to_domain))
    }

    /// Load the user by name and verify the password with
    /// `domain::security::verify_password`. Returns `None` when the name is
    /// unknown or the hash does not match (mirrors Python
    /// `check_password` -> `_verify` which swallows all exceptions).
    async fn authenticate(&self, name: &str, password: &str) -> Result<Option<User>, RepoError> {
        let row = user::Entity::find()
            .filter(user::Column::Name.eq(name))
            .one(&self.db)
            .await
            .map_err(translate_err)?;
        match row {
            Some(u) => {
                let hashed = u.password.clone().unwrap_or_default();
                if domain::security::verify_password(password, &hashed) {
                    Ok(Some(to_domain(u)))
                } else {
                    Ok(None)
                }
            }
            None => Ok(None),
        }
    }
}
