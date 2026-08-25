//! Migration 3: `page_views` — server-side visit analytics. One row per
//! full-page HTML load: when it happened, the normalized referrer host (NULL
//! for direct visits), the landing path, and a salted SHA-256 hash of the
//! client IP (raw IPs are never stored).

use sea_orm_migration::prelude::*;

#[derive(DeriveMigrationName)]
pub struct Migration;

#[async_trait::async_trait]
impl MigrationTrait for Migration {
    async fn up(&self, manager: &SchemaManager) -> Result<(), DbErr> {
        manager
            .create_table(
                Table::create()
                    .table(PageViews::Table)
                    .if_not_exists()
                    .col(
                        ColumnDef::new(PageViews::Id)
                            .integer()
                            .not_null()
                            .auto_increment()
                            .primary_key(),
                    )
                    .col(
                        ColumnDef::new(PageViews::VisitedAt)
                            .timestamp_with_time_zone()
                            .not_null(),
                    )
                    .col(ColumnDef::new(PageViews::Referrer).string_len(255).null())
                    .col(ColumnDef::new(PageViews::Path).string_len(255).not_null())
                    .col(ColumnDef::new(PageViews::IpHash).string_len(64).null())
                    .to_owned(),
            )
            .await?;
        // Separate statement: SQLite rejects the inline `INDEX(col)` table
        // syntax sea-query emits for `Table::create().index(...)`.
        manager
            .create_index(
                Index::create()
                    .name("idx-page-views-visited_at")
                    .table(PageViews::Table)
                    .col(PageViews::VisitedAt)
                    .to_owned(),
            )
            .await
    }

    async fn down(&self, manager: &SchemaManager) -> Result<(), DbErr> {
        manager
            .drop_table(Table::drop().table(PageViews::Table).to_owned())
            .await
    }
}

#[derive(Iden)]
enum PageViews {
    Table,
    Id,
    VisitedAt,
    Referrer,
    Path,
    IpHash,
}
