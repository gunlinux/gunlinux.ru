//! `users` table entity.

use sea_orm::entity::prelude::*;

#[derive(Clone, Debug, PartialEq, DeriveEntityModel, Eq)]
#[sea_orm(table_name = "users")]
pub struct Model {
    #[sea_orm(primary_key)]
    pub id: i32,
    #[sea_orm(column_type = "String(sea_orm::sea_query::StringLen::N(50))")]
    pub name: String,
    #[sea_orm(
        column_type = "String(sea_orm::sea_query::StringLen::N(255))",
        nullable
    )]
    pub password: Option<String>,
    /// Python: `Column("authenticated", Integer, default=0)` — nullable
    /// INTEGER, value written by the repository on every insert/update.
    pub authenticated: Option<i32>,
    pub createdon: Option<DateTimeUtc>,
}

#[derive(Copy, Clone, Debug, EnumIter, DeriveRelation)]
pub enum Relation {
    #[sea_orm(has_many = "super::post::Entity")]
    Posts,
}

impl Related<super::post::Entity> for Entity {
    fn to() -> RelationDef {
        Relation::Posts.def()
    }
}

impl ActiveModelBehavior for ActiveModel {}
