//! `tags` table entity.

use sea_orm::entity::prelude::*;

#[derive(Clone, Debug, PartialEq, DeriveEntityModel, Eq)]
#[sea_orm(table_name = "tags")]
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
}

#[derive(Copy, Clone, Debug, EnumIter, DeriveRelation)]
pub enum Relation {
    #[sea_orm(has_many = "super::posts_tag::Entity")]
    PostsTags,
}

impl Related<super::posts_tag::Entity> for Entity {
    fn to() -> RelationDef {
        Relation::PostsTags.def()
    }
}

impl Related<super::post::Entity> for Entity {
    fn to() -> RelationDef {
        super::posts_tag::Relation::Post.def()
    }
    fn via() -> Option<RelationDef> {
        Some(super::posts_tag::Relation::Tag.def().rev())
    }
}

impl ActiveModelBehavior for ActiveModel {}
