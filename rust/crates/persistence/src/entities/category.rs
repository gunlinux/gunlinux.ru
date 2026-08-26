//! `categories` table entity.

use sea_orm::entity::prelude::*;

#[derive(Clone, Debug, PartialEq, DeriveEntityModel, Eq)]
#[sea_orm(table_name = "categories")]
pub struct Model {
    #[sea_orm(primary_key)]
    pub id: i32,
    #[sea_orm(
        column_type = "String(sea_orm::sea_query::StringLen::N(255))",
        nullable
    )]
    pub title: Option<String>,
    #[sea_orm(
        column_type = "String(sea_orm::sea_query::StringLen::N(255))",
        nullable,
        unique
    )]
    pub alias: Option<String>,
    #[sea_orm(
        column_type = "String(sea_orm::sea_query::StringLen::N(255))",
        nullable
    )]
    pub template: Option<String>,
    /// Nullable BOOLEAN, no server default; `NULL` reads as `false`.
    pub page: Option<bool>,
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
