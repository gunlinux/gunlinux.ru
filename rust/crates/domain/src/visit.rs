//! Visit tracking (server-side analytics, added in the rewrite to replace
//! third-party metrika scripts).
//!
//! Every full-page HTML load is recorded once: where the visitor came from
//! (normalized referrer host), which page they landed on, and a salted hash of
//! their IP (raw IPs are never stored — `SECRET_KEY` salts the hash so unique
//! visitor counts work without keeping personally identifiable data).

use async_trait::async_trait;
use chrono::{DateTime, NaiveDate, Utc};
use serde::Serialize;

use crate::error::RepoError;

/// One recorded page view.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Visit {
    pub id: Option<i32>,
    pub visited_at: DateTime<Utc>,
    /// Normalized referrer host (`example.com`), `None` for direct visits.
    pub referrer: Option<String>,
    /// Landing path (path + query) of the viewed page.
    pub path: String,
    /// `sha256(ip + SECRET_KEY)` hex — never the raw IP.
    pub ip_hash: Option<String>,
}

/// Referrer source with its view count. `referrer: None` = direct entry.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct SourceCount {
    pub referrer: Option<String>,
    pub count: i64,
}

/// Views for one calendar day.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct DailyCount {
    pub day: NaiveDate,
    pub count: i64,
}

/// Landing page with its view count.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct PathCount {
    pub path: String,
    pub count: i64,
}

/// Analytics port. `persistence` implements it for real databases; `web`
/// depends only on the trait so routes and the admin stats page stay
/// database-platform independent.
#[async_trait]
pub trait VisitRepository: Send + Sync {
    /// Insert one visit. `id` is assigned by the backend and not returned.
    async fn record(&self, visit: &Visit) -> Result<(), RepoError>;
    /// Total recorded views, optionally limited to `since`.
    async fn total_views(&self, since: Option<DateTime<Utc>>) -> Result<i64, RepoError>;
    /// Distinct visitors (by `ip_hash`), optionally limited to `since`.
    async fn unique_visitors(&self, since: Option<DateTime<Utc>>) -> Result<i64, RepoError>;
    /// View counts per referrer source, most viewed first (`limit` rows).
    async fn referrer_counts(
        &self,
        since: Option<DateTime<Utc>>,
        limit: i32,
    ) -> Result<Vec<SourceCount>, RepoError>;
    /// View counts per landing page, most viewed first (`limit` rows).
    async fn top_paths(
        &self,
        since: Option<DateTime<Utc>>,
        limit: i32,
    ) -> Result<Vec<PathCount>, RepoError>;
    /// View counts for the last `days` days, oldest first. Days without views
    /// are omitted — callers pad the range for charts.
    async fn daily_counts(&self, days: i32) -> Result<Vec<DailyCount>, RepoError>;
}
