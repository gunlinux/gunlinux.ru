//! Baseline migration: creates the six tables exactly as defined by the
//! original schema.
//!
//! Column types / nullability / uniqueness match the original definitions:
//! - `users.id`, `posts.id`, `categories.id`, `tags.id`, `icons.id` — INTEGER PK
//! - `users.authenticated` — nullable BOOLEAN, no server default (prod schema;
//!   the repository always writes a value, `NULL` reads as `false`)
//! - `categories.page` — nullable BOOLEAN, no server default (same reasoning)
//! - `createdon` / `publishedon` — timezone-aware datetimes: Postgres
//!   `TIMESTAMPTZ`; SQLite stores values as ISO-8601 text (sea-query declares
//!   the column `timestamp_with_timezone_text`, which has TEXT affinity —
//!   equivalent to storing aware datetime ISO strings).
//! - `posts_tags` — pure join table; composite `(post_id, tag_id)` PK.
//!   FK actions default to NO ACTION.

use sea_orm_migration::prelude::*;

#[derive(DeriveMigrationName)]
pub struct Migration;

#[async_trait::async_trait]
impl MigrationTrait for Migration {
    async fn up(&self, manager: &SchemaManager) -> Result<(), DbErr> {
        // `users` and `categories` first — `posts` references both.
        manager
            .create_table(
                Table::create()
                    .table(Users::Table)
                    .if_not_exists()
                    .col(
                        ColumnDef::new(Users::Id)
                            .integer()
                            .not_null()
                            .auto_increment()
                            .primary_key(),
                    )
                    .col(ColumnDef::new(Users::Name).string_len(50).not_null())
                    .col(ColumnDef::new(Users::Password).string_len(255).null())
                    .col(ColumnDef::new(Users::Authenticated).boolean().null())
                    .col(
                        ColumnDef::new(Users::Createdon)
                            .timestamp_with_time_zone()
                            .null(),
                    )
                    .to_owned(),
            )
            .await?;

        manager
            .create_table(
                Table::create()
                    .table(Categories::Table)
                    .if_not_exists()
                    .col(
                        ColumnDef::new(Categories::Id)
                            .integer()
                            .not_null()
                            .auto_increment()
                            .primary_key(),
                    )
                    .col(ColumnDef::new(Categories::Title).string_len(255).null())
                    .col(
                        ColumnDef::new(Categories::Alias)
                            .string_len(255)
                            .null()
                            .unique_key(),
                    )
                    .col(ColumnDef::new(Categories::Template).string_len(255).null())
                    .col(ColumnDef::new(Categories::Page).boolean().null())
                    .to_owned(),
            )
            .await?;

        manager
            .create_table(
                Table::create()
                    .table(Posts::Table)
                    .if_not_exists()
                    .col(
                        ColumnDef::new(Posts::Id)
                            .integer()
                            .not_null()
                            .auto_increment()
                            .primary_key(),
                    )
                    .col(ColumnDef::new(Posts::Pagetitle).string_len(255).not_null())
                    .col(
                        ColumnDef::new(Posts::Alias)
                            .string_len(255)
                            .not_null()
                            .unique_key(),
                    )
                    .col(ColumnDef::new(Posts::Content).text().null())
                    .col(
                        ColumnDef::new(Posts::Createdon)
                            .timestamp_with_time_zone()
                            .null(),
                    )
                    .col(
                        ColumnDef::new(Posts::Publishedon)
                            .timestamp_with_time_zone()
                            .null(),
                    )
                    .col(ColumnDef::new(Posts::CategoryId).integer().null())
                    .col(ColumnDef::new(Posts::UserId).integer().null())
                    .foreign_key(
                        ForeignKey::create()
                            .name("fk-posts-category_id")
                            .from(Posts::Table, Posts::CategoryId)
                            .to(Categories::Table, Categories::Id),
                    )
                    .foreign_key(
                        ForeignKey::create()
                            .name("fk-posts-user_id")
                            .from(Posts::Table, Posts::UserId)
                            .to(Users::Table, Users::Id),
                    )
                    .to_owned(),
            )
            .await?;

        manager
            .create_table(
                Table::create()
                    .table(Tags::Table)
                    .if_not_exists()
                    .col(
                        ColumnDef::new(Tags::Id)
                            .integer()
                            .not_null()
                            .auto_increment()
                            .primary_key(),
                    )
                    .col(ColumnDef::new(Tags::Title).string_len(255).null())
                    .col(
                        ColumnDef::new(Tags::Alias)
                            .string_len(255)
                            .null()
                            .unique_key(),
                    )
                    .to_owned(),
            )
            .await?;

        manager
            .create_table(
                Table::create()
                    .table(PostsTags::Table)
                    .if_not_exists()
                    .col(ColumnDef::new(PostsTags::PostId).integer().not_null())
                    .col(ColumnDef::new(PostsTags::TagId).integer().not_null())
                    .primary_key(
                        Index::create()
                            .name("pk-posts_tags")
                            .col(PostsTags::PostId)
                            .col(PostsTags::TagId),
                    )
                    .foreign_key(
                        ForeignKey::create()
                            .name("fk-posts_tags-post_id")
                            .from(PostsTags::Table, PostsTags::PostId)
                            .to(Posts::Table, Posts::Id),
                    )
                    .foreign_key(
                        ForeignKey::create()
                            .name("fk-posts_tags-tag_id")
                            .from(PostsTags::Table, PostsTags::TagId)
                            .to(Tags::Table, Tags::Id),
                    )
                    .to_owned(),
            )
            .await?;

        manager
            .create_table(
                Table::create()
                    .table(Icons::Table)
                    .if_not_exists()
                    .col(
                        ColumnDef::new(Icons::Id)
                            .integer()
                            .not_null()
                            .auto_increment()
                            .primary_key(),
                    )
                    .col(
                        ColumnDef::new(Icons::Title)
                            .string_len(255)
                            .not_null()
                            .unique_key(),
                    )
                    .col(
                        ColumnDef::new(Icons::Url)
                            .string_len(255)
                            .not_null()
                            .unique_key(),
                    )
                    .col(ColumnDef::new(Icons::Content).text().null())
                    .to_owned(),
            )
            .await?;

        Ok(())
    }

    async fn down(&self, manager: &SchemaManager) -> Result<(), DbErr> {
        // Drop in reverse dependency order.
        manager
            .drop_table(Table::drop().table(PostsTags::Table).to_owned())
            .await?;
        manager
            .drop_table(Table::drop().table(Icons::Table).to_owned())
            .await?;
        manager
            .drop_table(Table::drop().table(Tags::Table).to_owned())
            .await?;
        manager
            .drop_table(Table::drop().table(Posts::Table).to_owned())
            .await?;
        manager
            .drop_table(Table::drop().table(Categories::Table).to_owned())
            .await?;
        manager
            .drop_table(Table::drop().table(Users::Table).to_owned())
            .await?;
        Ok(())
    }
}

#[derive(Iden)]
enum Users {
    Table,
    Id,
    Name,
    Password,
    Authenticated,
    Createdon,
}

#[derive(Iden)]
enum Categories {
    Table,
    Id,
    Title,
    Alias,
    Template,
    Page,
}

#[derive(Iden)]
enum Posts {
    Table,
    Id,
    Pagetitle,
    Alias,
    Content,
    Createdon,
    Publishedon,
    CategoryId,
    UserId,
}

#[derive(Iden)]
enum Tags {
    Table,
    Id,
    Title,
    Alias,
}

#[derive(Iden)]
enum PostsTags {
    Table,
    PostId,
    TagId,
}

#[derive(Iden)]
enum Icons {
    Table,
    Id,
    Title,
    Url,
    Content,
}
