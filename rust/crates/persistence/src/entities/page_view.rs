//! `page_views` table entity — server-side visit analytics.

use sea_orm::entity::prelude::*;

#[derive(Clone, Debug, PartialEq, DeriveEntityModel, Eq)]
#[sea_orm(table_name = "page_views")]
pub struct Model {
    #[sea_orm(primary_key)]
    pub id: i32,
    pub visited_at: DateTimeUtc,
    /// Normalized referrer host (`example.com`), `None` for direct visits.
    #[sea_orm(
        column_type = "String(sea_orm::sea_query::StringLen::N(255))",
        nullable
    )]
    pub referrer: Option<String>,
    /// Landing path (path + query) of the viewed page.
    #[sea_orm(column_type = "String(sea_orm::sea_query::StringLen::N(255))")]
    pub path: String,
    /// `sha256(ip + SECRET_KEY)` hex — never the raw IP.
    #[sea_orm(column_type = "String(sea_orm::sea_query::StringLen::N(64))", nullable)]
    pub ip_hash: Option<String>,
}

#[derive(Copy, Clone, Debug, EnumIter, DeriveRelation)]
pub enum Relation {}

impl ActiveModelBehavior for ActiveModel {}
