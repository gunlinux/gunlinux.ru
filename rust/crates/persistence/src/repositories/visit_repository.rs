//! `VisitRepository` — server-side visit analytics over the `page_views`
//! table. Backend-agnostic: grouping/aggregation uses standard SQL
//! (`GROUP BY` + `COUNT`), the distinct-visitor and per-day counts are
//! computed in Rust because `date_trunc`/`strftime` differ between Postgres
//! and SQLite and a personal blog's row volume makes that cheap.

use std::collections::{HashMap, HashSet};

use async_trait::async_trait;
use chrono::{DateTime, Duration, NaiveDate, Utc};
use sea_orm::{
    ActiveModelTrait, ColumnTrait, DatabaseConnection, EntityTrait, FromQueryResult,
    PaginatorTrait, QueryFilter, QuerySelect, Set,
};

use domain::VisitRepository as VisitRepoTrait;
use domain::{DailyCount, PathCount, RepoError, SourceCount, Visit};

use super::translate_err;
use crate::entities::page_view;

/// SeaORM-backed `VisitRepository`.
pub struct VisitRepository {
    db: DatabaseConnection,
}

impl VisitRepository {
    pub fn new(db: DatabaseConnection) -> Self {
        Self { db }
    }
}

#[derive(Debug, FromQueryResult)]
struct SourceRow {
    referrer: Option<String>,
    total: i64,
}

#[derive(Debug, FromQueryResult)]
struct PathRow {
    path: String,
    total: i64,
}

#[derive(Debug, FromQueryResult)]
struct IpHashRow {
    ip_hash: Option<String>,
}

#[async_trait]
impl VisitRepoTrait for VisitRepository {
    async fn record(&self, visit: &Visit) -> Result<(), RepoError> {
        page_view::ActiveModel {
            visited_at: Set(visit.visited_at),
            referrer: Set(visit.referrer.clone()),
            path: Set(visit.path.clone()),
            ip_hash: Set(visit.ip_hash.clone()),
            ..Default::default()
        }
        .insert(&self.db)
        .await
        .map_err(translate_err)?;
        Ok(())
    }

    async fn total_views(&self, since: Option<DateTime<Utc>>) -> Result<i64, RepoError> {
        let mut query = page_view::Entity::find();
        if let Some(since) = since {
            query = query.filter(page_view::Column::VisitedAt.gte(since));
        }
        Ok(query.count(&self.db).await.map_err(translate_err)? as i64)
    }

    async fn unique_visitors(&self, since: Option<DateTime<Utc>>) -> Result<i64, RepoError> {
        let mut query = page_view::Entity::find()
            .select_only()
            .column(page_view::Column::IpHash)
            .filter(page_view::Column::IpHash.is_not_null());
        if let Some(since) = since {
            query = query.filter(page_view::Column::VisitedAt.gte(since));
        }
        let rows = query
            .into_model::<IpHashRow>()
            .all(&self.db)
            .await
            .map_err(translate_err)?;
        let distinct = rows
            .into_iter()
            .filter_map(|r| r.ip_hash)
            .collect::<HashSet<_>>()
            .len();
        Ok(distinct as i64)
    }

    async fn referrer_counts(
        &self,
        since: Option<DateTime<Utc>>,
        limit: i32,
    ) -> Result<Vec<SourceCount>, RepoError> {
        let mut query = page_view::Entity::find()
            .select_only()
            .column(page_view::Column::Referrer)
            .column_as(page_view::Column::Id.count(), "total")
            .group_by(page_view::Column::Referrer);
        if let Some(since) = since {
            query = query.filter(page_view::Column::VisitedAt.gte(since));
        }
        let mut rows = query
            .into_model::<SourceRow>()
            .all(&self.db)
            .await
            .map_err(translate_err)?;
        // `ORDER BY <alias>` behaves differently on SQLite vs Postgres, so
        // sort here — the result set is small (≤ `limit` rows).
        rows.sort_by_key(|r| std::cmp::Reverse(r.total));
        rows.truncate(limit as usize);
        Ok(rows
            .into_iter()
            .map(|r| SourceCount {
                referrer: r.referrer,
                count: r.total,
            })
            .collect())
    }

    async fn top_paths(
        &self,
        since: Option<DateTime<Utc>>,
        limit: i32,
    ) -> Result<Vec<PathCount>, RepoError> {
        let mut query = page_view::Entity::find()
            .select_only()
            .column(page_view::Column::Path)
            .column_as(page_view::Column::Id.count(), "total")
            .group_by(page_view::Column::Path);
        if let Some(since) = since {
            query = query.filter(page_view::Column::VisitedAt.gte(since));
        }
        let mut rows = query
            .into_model::<PathRow>()
            .all(&self.db)
            .await
            .map_err(translate_err)?;
        rows.sort_by_key(|r| std::cmp::Reverse(r.total));
        rows.truncate(limit as usize);
        Ok(rows
            .into_iter()
            .map(|r| PathCount {
                path: r.path,
                count: r.total,
            })
            .collect())
    }

    async fn daily_counts(&self, days: i32) -> Result<Vec<DailyCount>, RepoError> {
        let since = Utc::now() - Duration::days(days as i64);
        let rows = page_view::Entity::find()
            .filter(page_view::Column::VisitedAt.gte(since))
            .all(&self.db)
            .await
            .map_err(translate_err)?;
        let mut by_day: HashMap<NaiveDate, i64> = HashMap::new();
        for row in rows {
            *by_day.entry(row.visited_at.date_naive()).or_default() += 1;
        }
        let mut counts: Vec<DailyCount> = by_day
            .into_iter()
            .map(|(day, count)| DailyCount { day, count })
            .collect();
        counts.sort_by_key(|c| c.day);
        Ok(counts)
    }
}
