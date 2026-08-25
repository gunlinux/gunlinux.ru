//! Migration 2: add `posts.update_date` — the content-version field for the
//! response cache. NULL for legacy rows (the cache version falls back to
//! `createdon`/`publishedon` via `COALESCE` semantics in `latest_update`).

use sea_orm_migration::prelude::*;

#[derive(DeriveMigrationName)]
pub struct Migration;

#[async_trait::async_trait]
impl MigrationTrait for Migration {
    async fn up(&self, manager: &SchemaManager) -> Result<(), DbErr> {
        manager
            .alter_table(
                Table::alter()
                    .table(Posts::Table)
                    .add_column(
                        ColumnDef::new(Posts::UpdateDate)
                            .timestamp_with_time_zone()
                            .null(),
                    )
                    .to_owned(),
            )
            .await
    }

    async fn down(&self, manager: &SchemaManager) -> Result<(), DbErr> {
        manager
            .alter_table(
                Table::alter()
                    .table(Posts::Table)
                    .drop_column(Posts::UpdateDate)
                    .to_owned(),
            )
            .await
    }
}

#[derive(Iden)]
enum Posts {
    Table,
    UpdateDate,
}
