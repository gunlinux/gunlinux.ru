//! Custom admin panel. Built entirely on the repository traits (the same
//! layer every other route uses; no ORM bypass). Generic CRUD is driven by
//! an `AdminModel` descriptor per entity plus a trait-object store over the
//! repositories.
//!
//! Auth: login via `UserService.authenticate_user`, JWT stored in the signed
//! `session` cookie, every non-auth `/admin` route redirects to
//! `/admin/login` when unauthenticated. On every write the `"blog"` response
//! cache is invalidated.
//!
//! Login attempts are throttled in-process in the previous implementation;
//! this app is a single process so throttling there is moot — intentionally
//! not ported.

use std::collections::HashMap;
use std::sync::Arc;

use application::admin as commands;
use async_trait::async_trait;
use axum::extract::{Path, Query, State};
use axum::http::{header, HeaderMap, StatusCode};
use axum::response::{IntoResponse, Response};
use axum::Router;
use chrono::{Duration, NaiveDate, Utc};
use domain::{CategoryRepository, IconRepository, PostRepository, TagRepository, UserRepository};
use minijinja::context;
use serde::Serialize;
use serde_json::Value as JsonValue;

use crate::app::AppState;
use crate::auth;
use crate::cache;
use crate::error::WebError;
use crate::templates::render;

/// Descriptor for one admin-managed model (column lists, searchable/sortable
/// fields, form-excluded fields).
#[derive(Debug, Clone, Serialize)]
pub struct AdminModel {
    pub name: &'static str,
    pub name_plural: &'static str,
    /// URL segment for this model.
    pub slug: &'static str,
    pub columns: &'static [&'static str],
    pub searchable: &'static [&'static str],
    pub sortable: &'static [&'static str],
    pub form_excluded: &'static [&'static str],
}

pub static POST_MODEL: AdminModel = AdminModel {
    name: "Post",
    name_plural: "Posts",
    slug: "post",
    columns: &["id", "pagetitle", "alias", "publishedon", "category_id"],
    searchable: &["pagetitle", "alias"],
    sortable: &["id", "publishedon"],
    form_excluded: &[],
};

pub static CATEGORY_MODEL: AdminModel = AdminModel {
    name: "Category",
    name_plural: "Categories",
    slug: "category",
    columns: &["id", "title", "alias", "page"],
    searchable: &["title", "alias"],
    sortable: &["id", "title"],
    form_excluded: &[],
};

pub static TAG_MODEL: AdminModel = AdminModel {
    name: "Tag",
    name_plural: "Tags",
    slug: "tag",
    columns: &["id", "title", "alias"],
    searchable: &["title", "alias"],
    sortable: &["id", "title"],
    form_excluded: &[],
};

pub static USER_MODEL: AdminModel = AdminModel {
    name: "User",
    name_plural: "Users",
    slug: "user",
    columns: &["id", "name", "createdon"],
    searchable: &["name"],
    sortable: &["id", "name"],
    form_excluded: &["password"],
};

pub static ICON_MODEL: AdminModel = AdminModel {
    name: "Icon",
    name_plural: "Icons",
    slug: "icon",
    columns: &["id", "title", "url"],
    searchable: &["title"],
    sortable: &["id", "title"],
    form_excluded: &[],
};

/// All model descriptors, in admin registration order.
pub static ALL_MODELS: &[&AdminModel] = &[
    &POST_MODEL,
    &CATEGORY_MODEL,
    &TAG_MODEL,
    &USER_MODEL,
    &ICON_MODEL,
];

/// How a form field is rendered in the generic create/edit form.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InputKind {
    Text,
    Textarea,
    Checkbox,
    Select,
    CheckboxGroup,
}

/// One `<option>` / checkbox chip in a select or multi-select field.
#[derive(Debug, Clone, Serialize)]
pub struct FormOption {
    pub value: String,
    pub label: String,
}

/// A trait-object view over one entity's repository, exposing the operations
/// the generic admin UI needs. Implementations translate form data into domain
/// entities and go through `Repository::create`/`update`/`delete` exactly like
/// every other code path.
#[async_trait]
pub trait AdminStore: Send + Sync {
    fn descriptor(&self) -> &'static AdminModel;
    fn form_fields(&self) -> &'static [&'static str];
    fn input_kind(&self, field: &str) -> InputKind;

    /// Option lists for select/checkbox fields (categories, tags, ...).
    /// Defaults to nothing; only stores with relational fields override it.
    async fn options(&self, _field: &str) -> Result<Vec<FormOption>, WebError> {
        Ok(Vec::new())
    }

    async fn list_rows(
        &self,
        search: Option<&str>,
        sort: Option<&str>,
    ) -> Result<Vec<JsonValue>, WebError>;
    async fn get_row(&self, id: i32) -> Result<Option<JsonValue>, WebError>;
    async fn create_from_form(&self, form: &HashMap<String, String>) -> Result<(), WebError>;
    async fn update_from_form(
        &self,
        id: i32,
        form: &HashMap<String, String>,
    ) -> Result<(), WebError>;
    async fn delete(&self, id: i32) -> Result<bool, WebError>;
}

// ---------------------------------------------------------------------------
// Generic row helpers
// ---------------------------------------------------------------------------

fn to_json<T: Serialize>(value: &T) -> JsonValue {
    serde_json::to_value(value).unwrap_or(JsonValue::Null)
}

fn filter_and_sort_rows(
    rows: Vec<JsonValue>,
    model: &AdminModel,
    search: Option<&str>,
    sort: Option<&str>,
    descending: bool,
) -> Vec<JsonValue> {
    let mut rows = rows;
    if let Some(q) = search.map(str::to_lowercase).filter(|q| !q.is_empty()) {
        rows.retain(|row| {
            model.searchable.iter().any(|field| {
                row.get(*field)
                    .and_then(JsonValue::as_str)
                    .map(|s| s.to_lowercase().contains(&q))
                    .unwrap_or(false)
            })
        });
    }
    let sort_field = sort.filter(|s| model.sortable.contains(s));
    match sort_field {
        Some(field) => rows.sort_by(|a, b| cmp_json(a.get(field), b.get(field))),
        None => rows.sort_by(|a, b| cmp_json(a.get("id"), b.get("id"))),
    }
    if descending {
        rows.reverse();
    }
    rows
}

fn cmp_json(a: Option<&JsonValue>, b: Option<&JsonValue>) -> std::cmp::Ordering {
    match (a, b) {
        (Some(JsonValue::Number(x)), Some(JsonValue::Number(y))) => x.as_i64().cmp(&y.as_i64()),
        (Some(JsonValue::String(x)), Some(JsonValue::String(y))) => x.cmp(y),
        (Some(_), Some(_)) => std::cmp::Ordering::Equal,
        (None, None) => std::cmp::Ordering::Equal,
        (None, Some(_)) => std::cmp::Ordering::Less,
        (Some(_), None) => std::cmp::Ordering::Greater,
    }
}

fn textarea_fields(store: &dyn AdminStore) -> Vec<&'static str> {
    store
        .form_fields()
        .iter()
        .copied()
        .filter(|f| store.input_kind(f) == InputKind::Textarea)
        .collect()
}

fn checkbox_fields(store: &dyn AdminStore) -> Vec<&'static str> {
    store
        .form_fields()
        .iter()
        .copied()
        .filter(|f| store.input_kind(f) == InputKind::Checkbox)
        .collect()
}

/// Option lists for every form field (only select/checkbox-group fields get
/// entries).
async fn collect_options(
    store: &dyn AdminStore,
) -> Result<HashMap<&'static str, Vec<FormOption>>, WebError> {
    let mut map = HashMap::new();
    for field in store.form_fields() {
        map.insert(*field, store.options(field).await?);
    }
    Ok(map)
}

// ---------------------------------------------------------------------------
// Per-model stores
// ---------------------------------------------------------------------------

pub struct PostStore {
    repo: Arc<dyn PostRepository>,
    tags: Arc<dyn TagRepository>,
    categories: Arc<dyn CategoryRepository>,
}

pub struct CategoryStore {
    repo: Arc<dyn CategoryRepository>,
}

pub struct TagStore {
    repo: Arc<dyn TagRepository>,
}

pub struct UserStore {
    repo: Arc<dyn UserRepository>,
}

pub struct IconStore {
    repo: Arc<dyn IconRepository>,
}

#[async_trait]
impl AdminStore for PostStore {
    fn descriptor(&self) -> &'static AdminModel {
        &POST_MODEL
    }
    fn form_fields(&self) -> &'static [&'static str] {
        &[
            "pagetitle",
            "alias",
            "content",
            "publishedon",
            "category_id",
            "tags",
            "is_page",
        ]
    }
    fn input_kind(&self, field: &str) -> InputKind {
        match field {
            "content" => InputKind::Textarea,
            "category_id" => InputKind::Select,
            "tags" => InputKind::CheckboxGroup,
            "is_page" => InputKind::Checkbox,
            _ => InputKind::Text,
        }
    }

    async fn options(&self, field: &str) -> Result<Vec<FormOption>, WebError> {
        match field {
            "category_id" => {
                let cats = self.categories.get_all().await?;
                Ok(cats
                    .iter()
                    .map(|c| FormOption {
                        value: c.id.map(|i| i.to_string()).unwrap_or_default(),
                        label: format!("{} ({})", c.title, c.alias),
                    })
                    .collect())
            }
            "tags" => {
                let tags = self.tags.get_all().await?;
                Ok(tags
                    .iter()
                    .map(|t| FormOption {
                        value: t.id.map(|i| i.to_string()).unwrap_or_default(),
                        label: t.title.clone(),
                    })
                    .collect())
            }
            _ => Ok(Vec::new()),
        }
    }

    async fn list_rows(
        &self,
        search: Option<&str>,
        sort: Option<&str>,
    ) -> Result<Vec<JsonValue>, WebError> {
        let rows = self.repo.get_all().await?.iter().map(to_json).collect();
        Ok(filter_and_sort_rows(
            rows,
            self.descriptor(),
            search,
            sort,
            false,
        ))
    }

    async fn get_row(&self, id: i32) -> Result<Option<JsonValue>, WebError> {
        let Some(post) = self.repo.get_by_id(id).await? else {
            return Ok(None);
        };
        let mut row = to_json(&post);
        // Normalize the relational fields to strings so the template can
        // compare them against option values, and expose the post's tags.
        if let Some(obj) = row.as_object_mut() {
            if let Some(cid) = obj.get("category_id").and_then(JsonValue::as_i64) {
                obj.insert("category_id".into(), JsonValue::String(cid.to_string()));
            }
            let tags = self.repo.get_tags_for_post(id).await?;
            let ids: Vec<JsonValue> = tags
                .iter()
                .filter_map(|t| t.id)
                .map(|i| JsonValue::String(i.to_string()))
                .collect();
            obj.insert("tags".into(), JsonValue::Array(ids));
        }
        Ok(Some(row))
    }

    async fn create_from_form(&self, form: &HashMap<String, String>) -> Result<(), WebError> {
        commands::create_post(&*self.repo, form).await?;
        Ok(())
    }

    async fn update_from_form(
        &self,
        id: i32,
        form: &HashMap<String, String>,
    ) -> Result<(), WebError> {
        commands::update_post(&*self.repo, id, form).await?;
        Ok(())
    }

    async fn delete(&self, id: i32) -> Result<bool, WebError> {
        Ok(commands::delete_post(&*self.repo, id).await?)
    }
}

#[async_trait]
impl AdminStore for CategoryStore {
    fn descriptor(&self) -> &'static AdminModel {
        &CATEGORY_MODEL
    }
    fn form_fields(&self) -> &'static [&'static str] {
        &["title", "alias", "template", "page"]
    }
    fn input_kind(&self, field: &str) -> InputKind {
        match field {
            "page" => InputKind::Checkbox,
            _ => InputKind::Text,
        }
    }

    async fn list_rows(
        &self,
        search: Option<&str>,
        sort: Option<&str>,
    ) -> Result<Vec<JsonValue>, WebError> {
        let rows = self.repo.get_all().await?.iter().map(to_json).collect();
        Ok(filter_and_sort_rows(
            rows,
            self.descriptor(),
            search,
            sort,
            false,
        ))
    }

    async fn get_row(&self, id: i32) -> Result<Option<JsonValue>, WebError> {
        Ok(self.repo.get_by_id(id).await?.map(|c| to_json(&c)))
    }

    async fn create_from_form(&self, form: &HashMap<String, String>) -> Result<(), WebError> {
        commands::create_category(&*self.repo, form).await?;
        Ok(())
    }

    async fn update_from_form(
        &self,
        id: i32,
        form: &HashMap<String, String>,
    ) -> Result<(), WebError> {
        commands::update_category(&*self.repo, id, form).await?;
        Ok(())
    }

    async fn delete(&self, id: i32) -> Result<bool, WebError> {
        Ok(self.repo.delete(id).await?)
    }
}

#[async_trait]
impl AdminStore for TagStore {
    fn descriptor(&self) -> &'static AdminModel {
        &TAG_MODEL
    }
    fn form_fields(&self) -> &'static [&'static str] {
        &["title", "alias"]
    }
    fn input_kind(&self, _field: &str) -> InputKind {
        InputKind::Text
    }

    async fn list_rows(
        &self,
        search: Option<&str>,
        sort: Option<&str>,
    ) -> Result<Vec<JsonValue>, WebError> {
        let rows = self.repo.get_all().await?.iter().map(to_json).collect();
        Ok(filter_and_sort_rows(
            rows,
            self.descriptor(),
            search,
            sort,
            false,
        ))
    }

    async fn get_row(&self, id: i32) -> Result<Option<JsonValue>, WebError> {
        Ok(self.repo.get_by_id(id).await?.map(|t| to_json(&t)))
    }

    async fn create_from_form(&self, form: &HashMap<String, String>) -> Result<(), WebError> {
        commands::create_tag(&*self.repo, form).await?;
        Ok(())
    }

    async fn update_from_form(
        &self,
        id: i32,
        form: &HashMap<String, String>,
    ) -> Result<(), WebError> {
        commands::update_tag(&*self.repo, id, form).await?;
        Ok(())
    }

    async fn delete(&self, id: i32) -> Result<bool, WebError> {
        Ok(self.repo.delete(id).await?)
    }
}

#[async_trait]
impl AdminStore for UserStore {
    fn descriptor(&self) -> &'static AdminModel {
        &USER_MODEL
    }
    fn form_fields(&self) -> &'static [&'static str] {
        &["name", "password", "authenticated"]
    }
    fn input_kind(&self, field: &str) -> InputKind {
        match field {
            "authenticated" => InputKind::Checkbox,
            _ => InputKind::Text,
        }
    }

    async fn list_rows(
        &self,
        search: Option<&str>,
        sort: Option<&str>,
    ) -> Result<Vec<JsonValue>, WebError> {
        let rows = self.repo.get_all().await?.iter().map(to_json).collect();
        Ok(filter_and_sort_rows(
            rows,
            self.descriptor(),
            search,
            sort,
            false,
        ))
    }

    async fn get_row(&self, id: i32) -> Result<Option<JsonValue>, WebError> {
        Ok(self.repo.get_by_id(id).await?.map(|u| to_json(&u)))
    }

    async fn create_from_form(&self, form: &HashMap<String, String>) -> Result<(), WebError> {
        commands::create_user(&*self.repo, form).await?;
        Ok(())
    }

    async fn update_from_form(
        &self,
        id: i32,
        form: &HashMap<String, String>,
    ) -> Result<(), WebError> {
        commands::update_user(&*self.repo, id, form).await?;
        Ok(())
    }

    async fn delete(&self, id: i32) -> Result<bool, WebError> {
        Ok(self.repo.delete(id).await?)
    }
}

#[async_trait]
impl AdminStore for IconStore {
    fn descriptor(&self) -> &'static AdminModel {
        &ICON_MODEL
    }
    fn form_fields(&self) -> &'static [&'static str] {
        &["title", "url", "content"]
    }
    fn input_kind(&self, field: &str) -> InputKind {
        match field {
            "content" => InputKind::Textarea,
            _ => InputKind::Text,
        }
    }

    async fn list_rows(
        &self,
        search: Option<&str>,
        sort: Option<&str>,
    ) -> Result<Vec<JsonValue>, WebError> {
        let rows = self.repo.get_all().await?.iter().map(to_json).collect();
        Ok(filter_and_sort_rows(
            rows,
            self.descriptor(),
            search,
            sort,
            false,
        ))
    }

    async fn get_row(&self, id: i32) -> Result<Option<JsonValue>, WebError> {
        Ok(self.repo.get_by_id(id).await?.map(|i| to_json(&i)))
    }

    async fn create_from_form(&self, form: &HashMap<String, String>) -> Result<(), WebError> {
        commands::create_icon(&*self.repo, form).await?;
        Ok(())
    }

    async fn update_from_form(
        &self,
        id: i32,
        form: &HashMap<String, String>,
    ) -> Result<(), WebError> {
        commands::update_icon(&*self.repo, id, form).await?;
        Ok(())
    }

    async fn delete(&self, id: i32) -> Result<bool, WebError> {
        Ok(self.repo.delete(id).await?)
    }
}

/// Build a store trait object for the given model name (accepts singular and
/// plural URL segments, e.g. `/admin/posts/...`).
pub fn admin_store_for(state: &AppState, model: &str) -> Option<Box<dyn AdminStore>> {
    match model {
        "post" | "posts" => Some(Box::new(PostStore {
            repo: state.posts.clone(),
            tags: state.tags.clone(),
            categories: state.categories.clone(),
        })),
        "category" | "categories" => Some(Box::new(CategoryStore {
            repo: state.categories.clone(),
        })),
        "tag" | "tags" => Some(Box::new(TagStore {
            repo: state.tags.clone(),
        })),
        "user" | "users" => Some(Box::new(UserStore {
            repo: state.users.clone(),
        })),
        "icon" | "icons" => Some(Box::new(IconStore {
            repo: state.icons.clone(),
        })),
        _ => None,
    }
}

// ---------------------------------------------------------------------------
// Auth helpers
// ---------------------------------------------------------------------------

fn redirect_to_login() -> Response {
    (StatusCode::FOUND, [(header::LOCATION, "/admin/login")]).into_response()
}

fn redirect(uri: &str) -> Response {
    (StatusCode::SEE_OTHER, [(header::LOCATION, uri)]).into_response()
}

/// The authenticated user name from the signed session cookie, if any.
fn admin_username(state: &AppState, headers: &HeaderMap) -> Option<String> {
    let cookie_header = headers.get(header::COOKIE)?.to_str().ok()?;
    let cookie = auth::cookie_value(cookie_header, auth::SESSION_COOKIE_NAME)?;
    let token = auth::read_access_token(&cookie, state.settings.secret_key.as_bytes())?;
    auth::decode_token(&token, &state.settings)
}

fn set_cookie_on(resp: &mut Response, header_value: String) {
    resp.headers_mut().insert(
        header::SET_COOKIE,
        header_value.parse().expect("valid Set-Cookie"),
    );
}

fn html_response(body: String) -> Response {
    ([(header::CONTENT_TYPE, "text/html; charset=utf-8")], body).into_response()
}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

async fn dashboard(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> Result<Response, WebError> {
    if admin_username(&state, &headers).is_none() {
        return Ok(redirect_to_login());
    }
    let mut counts = HashMap::new();
    counts.insert("post", state.posts.get_all().await?.len());
    counts.insert("category", state.categories.get_all().await?.len());
    counts.insert("tag", state.tags.get_all().await?.len());
    counts.insert("user", state.users.get_all().await?.len());
    counts.insert("icon", state.icons.get_all().await?.len());
    let body = render(
        &state.templates,
        "admin/dashboard.html",
        context! {
            models => ALL_MODELS,
            counts => counts,
            views_total => state.visits.total_views(None).await?,
        },
    )?;
    Ok(html_response(body))
}

/// Days of daily-chart data shown on the stats page.
const STATS_DAILY_DAYS: i64 = 14;
/// View-count rows shown per table on the stats page.
const STATS_TOP_LIMIT: i32 = 10;

/// A source row for the stats template: `None` referrer rendered as "direct".
#[derive(Debug, Clone, Serialize)]
struct SourceView {
    label: String,
    count: i64,
}

/// One bar of the daily views chart.
#[derive(Debug, Clone, Serialize)]
struct DayBar {
    label: String,
    count: i64,
    /// Bar height as a percentage of the busiest day (0 when empty).
    pct: u32,
}

/// Pad the repository's daily counts to a contiguous `days`-long range ending
/// today (days without views get a zero bar).
fn pad_daily_counts(counts: Vec<domain::DailyCount>, days: i64) -> Vec<DayBar> {
    let today = Utc::now().date_naive();
    let by_day: std::collections::HashMap<NaiveDate, i64> =
        counts.into_iter().map(|c| (c.day, c.count)).collect();
    let mut bars: Vec<DayBar> = (0..days)
        .map(|offset| {
            let day = today - Duration::days(days - 1 - offset);
            let count = by_day.get(&day).copied().unwrap_or(0);
            DayBar {
                label: day.format("%d.%m").to_string(),
                count,
                pct: 0,
            }
        })
        .collect();
    let max = bars.iter().map(|b| b.count).max().unwrap_or(0).max(1);
    for bar in &mut bars {
        bar.pct = ((bar.count as f64 / max as f64) * 100.0).round() as u32;
    }
    bars
}

/// `GET /admin/stats` — server-side visit analytics: totals, unique visitors,
/// a daily bar chart, top referrer sources and top landing pages.
async fn stats(State(state): State<AppState>, headers: HeaderMap) -> Result<Response, WebError> {
    if admin_username(&state, &headers).is_none() {
        return Ok(redirect_to_login());
    }
    let since_30d = Some(Utc::now() - Duration::days(30));
    let sources: Vec<SourceView> = state
        .visits
        .referrer_counts(since_30d, STATS_TOP_LIMIT)
        .await?
        .into_iter()
        .map(|s| SourceView {
            label: s.referrer.unwrap_or_else(|| "direct".to_string()),
            count: s.count,
        })
        .collect();
    let paths = state.visits.top_paths(since_30d, STATS_TOP_LIMIT).await?;
    let daily = pad_daily_counts(
        state.visits.daily_counts(STATS_DAILY_DAYS as i32).await?,
        STATS_DAILY_DAYS,
    );
    let body = render(
        &state.templates,
        "admin/stats.html",
        context! {
            models => ALL_MODELS,
            total_views => state.visits.total_views(None).await?,
            views_30d => state.visits.total_views(since_30d).await?,
            unique_30d => state.visits.unique_visitors(since_30d).await?,
            sources => sources,
            paths => paths,
            daily => daily,
        },
    )?;
    Ok(html_response(body))
}

async fn login_get(State(state): State<AppState>) -> Result<Response, WebError> {
    let body = render(
        &state.templates,
        "admin/login.html",
        context! { error => None::<&str> },
    )?;
    Ok(html_response(body))
}

async fn login_post(
    State(state): State<AppState>,
    axum::Form(form): axum::Form<HashMap<String, String>>,
) -> Result<Response, WebError> {
    let username = form.get("username").cloned().unwrap_or_default();
    let password = form.get("password").cloned().unwrap_or_default();
    if let Some(user) = state.users.authenticate(&username, &password).await? {
        let token = auth::create_access_token(&user.name, &state.settings)
            .map_err(|e| WebError::Internal(format!("jwt: {e}")))?;
        let mut resp = redirect("/admin");
        set_cookie_on(
            &mut resp,
            auth::set_cookie_header(&token, state.settings.secret_key.as_bytes()),
        );
        Ok(resp)
    } else {
        let body = render(
            &state.templates,
            "admin/login.html",
            context! { error => Some("Invalid username or password") },
        )?;
        Ok(html_response(body))
    }
}

async fn logout() -> Response {
    let mut resp = redirect_to_login();
    set_cookie_on(&mut resp, auth::clear_access_token());
    resp
}

/// Rows per list page.
const PAGE_SIZE: usize = 25;

async fn list(
    State(state): State<AppState>,
    Path(model): Path<String>,
    Query(params): Query<HashMap<String, String>>,
    headers: HeaderMap,
) -> Result<Response, WebError> {
    if admin_username(&state, &headers).is_none() {
        return Ok(redirect_to_login());
    }
    let Some(store) = admin_store_for(&state, &model) else {
        return Ok(crate::routes::not_found());
    };
    let search = params.get("search").map(String::as_str);
    let sort = params.get("sort").map(String::as_str);
    let descending = params.get("dir").is_some_and(|d| d == "desc");
    let mut rows = store.list_rows(search, sort).await?;
    if descending {
        rows.reverse();
    }
    let total = rows.len();
    let pages = total.div_ceil(PAGE_SIZE).max(1);
    let page = params
        .get("page")
        .and_then(|p| p.parse::<usize>().ok())
        .unwrap_or(1)
        .clamp(1, pages);
    let start = (page - 1) * PAGE_SIZE;
    let page_rows: Vec<JsonValue> = rows.into_iter().skip(start).take(PAGE_SIZE).collect();

    let ctx = context! {
        model => store.descriptor(),
        models => ALL_MODELS,
        rows => page_rows,
        search => params.get("search").cloned().unwrap_or_default(),
        sort => sort.unwrap_or(""),
        dir => if descending { "desc" } else { "asc" },
        page => page,
        pages => pages,
        total => total,
    };
    // htmx requests (search-as-you-type, pagination) swap only the table.
    let template = if headers.contains_key(header::HeaderName::from_static("hx-request")) {
        "admin/list_table.html"
    } else {
        "admin/list.html"
    };
    let body = render(&state.templates, template, ctx)?;
    Ok(html_response(body))
}

async fn create_form(
    State(state): State<AppState>,
    Path(model): Path<String>,
    headers: HeaderMap,
) -> Result<Response, WebError> {
    if admin_username(&state, &headers).is_none() {
        return Ok(redirect_to_login());
    }
    let Some(store) = admin_store_for(&state, &model) else {
        return Ok(crate::routes::not_found());
    };
    let options = collect_options(store.as_ref()).await?;
    let body = render(
        &state.templates,
        "admin/form.html",
        context! {
            model => store.descriptor(),
            models => ALL_MODELS,
            fields => store.form_fields(),
            textareas => textarea_fields(store.as_ref()),
            checkboxes => checkbox_fields(store.as_ref()),
            options => options,
            values => JsonValue::Object(Default::default()),
            action => format!("/admin/{}/create", store.descriptor().slug),
            is_create => true,
            error => None::<&str>,
        },
    )?;
    Ok(html_response(body))
}

async fn create(
    State(state): State<AppState>,
    Path(model): Path<String>,
    headers: HeaderMap,
    axum::Form(form): axum::Form<HashMap<String, String>>,
) -> Result<Response, WebError> {
    if admin_username(&state, &headers).is_none() {
        return Ok(redirect_to_login());
    }
    let Some(store) = admin_store_for(&state, &model) else {
        return Ok(crate::routes::not_found());
    };
    match store.create_from_form(&form).await {
        Ok(()) => {
            state.cache.clear_namespace(cache::NAMESPACE).await;
            Ok(redirect(&format!("/admin/{}/", store.descriptor().slug)))
        }
        Err(e) => render_form_error(&state, store.as_ref(), &form, None, e).await,
    }
}

async fn edit_form(
    State(state): State<AppState>,
    Path((model, id)): Path<(String, i32)>,
    headers: HeaderMap,
) -> Result<Response, WebError> {
    if admin_username(&state, &headers).is_none() {
        return Ok(redirect_to_login());
    }
    let Some(store) = admin_store_for(&state, &model) else {
        return Ok(crate::routes::not_found());
    };
    let Some(values) = store.get_row(id).await? else {
        return Ok(crate::routes::not_found());
    };
    let options = collect_options(store.as_ref()).await?;
    let body = render(
        &state.templates,
        "admin/form.html",
        context! {
            model => store.descriptor(),
            models => ALL_MODELS,
            fields => store.form_fields(),
            textareas => textarea_fields(store.as_ref()),
            checkboxes => checkbox_fields(store.as_ref()),
            options => options,
            values => values,
            action => format!("/admin/{}/{id}/edit", store.descriptor().slug),
            is_create => false,
            error => None::<&str>,
        },
    )?;
    Ok(html_response(body))
}

async fn edit(
    State(state): State<AppState>,
    Path((model, id)): Path<(String, i32)>,
    headers: HeaderMap,
    axum::Form(form): axum::Form<HashMap<String, String>>,
) -> Result<Response, WebError> {
    if admin_username(&state, &headers).is_none() {
        return Ok(redirect_to_login());
    }
    let Some(store) = admin_store_for(&state, &model) else {
        return Ok(crate::routes::not_found());
    };
    match store.update_from_form(id, &form).await {
        Ok(()) => {
            state.cache.clear_namespace(cache::NAMESPACE).await;
            Ok(redirect(&format!("/admin/{}/", store.descriptor().slug)))
        }
        Err(e) => render_form_error(&state, store.as_ref(), &form, Some(id), e).await,
    }
}

async fn delete(
    State(state): State<AppState>,
    Path((model, id)): Path<(String, i32)>,
    headers: HeaderMap,
) -> Result<Response, WebError> {
    if admin_username(&state, &headers).is_none() {
        return Ok(redirect_to_login());
    }
    let Some(store) = admin_store_for(&state, &model) else {
        return Ok(crate::routes::not_found());
    };
    store.delete(id).await?;
    state.cache.clear_namespace(cache::NAMESPACE).await;
    Ok(redirect(&format!("/admin/{}/", store.descriptor().slug)))
}

/// Re-render the create/edit form with the error message, preserving the
/// submitted field values. `NotFound` maps to a plain 404 page.
async fn render_form_error(
    state: &AppState,
    store: &dyn AdminStore,
    form: &HashMap<String, String>,
    id: Option<i32>,
    error: WebError,
) -> Result<Response, WebError> {
    match error {
        WebError::NotFound => Ok(crate::routes::not_found()),
        e => {
            let mut map = serde_json::Map::new();
            for field in store.form_fields() {
                if let Some(v) = form.get(*field) {
                    // The hidden `tags` input is comma-joined; split it back
                    // into the array the checkbox chips expect.
                    let value = if *field == "tags" {
                        JsonValue::Array(
                            v.split(',')
                                .filter_map(|s| s.trim().parse::<i32>().ok())
                                .map(|i| JsonValue::String(i.to_string()))
                                .collect(),
                        )
                    } else {
                        JsonValue::String(v.clone())
                    };
                    map.insert(field.to_string(), value);
                }
            }
            let options = collect_options(store).await?;
            let action = match id {
                Some(id) => format!("/admin/{}/{id}/edit", store.descriptor().slug),
                None => format!("/admin/{}/create", store.descriptor().slug),
            };
            let body = render(
                &state.templates,
                "admin/form.html",
                context! {
                    model => store.descriptor(),
                    models => ALL_MODELS,
                    fields => store.form_fields(),
                    textareas => textarea_fields(store),
                    checkboxes => checkbox_fields(store),
                    options => options,
                    values => JsonValue::Object(map),
                    action => action,
                    is_create => id.is_none(),
                    error => Some(e.to_string()),
                },
            )?;
            Ok(html_response(body))
        }
    }
}

/// Admin routes. Merged into the main router BEFORE the catch-all `/{alias}`.
pub fn router() -> Router<AppState> {
    use axum::routing::get;
    Router::new()
        .route("/admin", get(dashboard))
        .route("/admin/", get(dashboard)) // the admin index is served at /admin/
        .route("/admin/login", get(login_get).post(login_post))
        .route("/admin/logout", get(logout))
        .route("/admin/stats", get(stats))
        .route("/admin/{model}", get(list))
        .route("/admin/{model}/", get(list))
        .route("/admin/{model}/create", get(create_form).post(create))
        .route("/admin/{model}/{id}/edit", get(edit_form).post(edit))
        .route("/admin/{model}/{id}/delete", get(delete).post(delete))
}
