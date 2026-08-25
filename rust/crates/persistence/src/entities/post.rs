//! `posts` table entity.

use sea_orm::entity::prelude::*;

#[derive(Clone, Debug, PartialEq, DeriveEntityModel, Eq)]
#[sea_orm(table_name = "posts")]
pub struct Model {
    #[sea_orm(primary_key)]
    pub id: i32,
    #[sea_orm(column_type = "String(sea_orm::sea_query::StringLen::N(255))")]
    pub pagetitle: String,
    #[sea_orm(column_type = "String(sea_orm::sea_query::StringLen::N(255))", unique)]
    pub alias: String,
    #[sea_orm(column_type = "Text", nullable)]
    pub content: Option<String>,
    pub createdon: Option<DateTimeUtc>,
    pub publishedon: Option<DateTimeUtc>,
    /// Set on create/update by the admin layer; NULL for legacy rows. Drives
    /// the response cache's content version.
    pub update_date: Option<DateTimeUtc>,
    pub category_id: Option<i32>,
    pub user_id: Option<i32>,
}

#[derive(Copy, Clone, Debug, EnumIter, DeriveRelation)]
pub enum Relation {
    #[sea_orm(has_many = "super::posts_tag::Entity")]
    PostsTags,
    #[sea_orm(
        belongs_to = "super::category::Entity",
        from = "Column::CategoryId",
        to = "super::category::Column::Id"
    )]
    Category,
    #[sea_orm(
        belongs_to = "super::user::Entity",
        from = "Column::UserId",
        to = "super::user::Column::Id"
    )]
    User,
}

impl Related<super::posts_tag::Entity> for Entity {
    fn to() -> RelationDef {
        Relation::PostsTags.def()
    }
}

impl Related<super::category::Entity> for Entity {
    fn to() -> RelationDef {
        Relation::Category.def()
    }
}

impl Related<super::user::Entity> for Entity {
    fn to() -> RelationDef {
        Relation::User.def()
    }
}

impl Related<super::tag::Entity> for Entity {
    fn to() -> RelationDef {
        super::posts_tag::Relation::Tag.def()
    }
    fn via() -> Option<RelationDef> {
        Some(super::posts_tag::Relation::Post.def().rev())
    }
}

impl ActiveModelBehavior for ActiveModel {}
