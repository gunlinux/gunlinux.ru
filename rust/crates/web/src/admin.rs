//! Custom admin panel — replaces sqladmin. Built entirely on the repository
//! traits (the same layer every other route uses; no ORM bypass like the
//! Python sqladmin). Generic CRUD is driven by an `AdminModel` descriptor per
//! entity plus a trait-object store over the repositories.
//!
//! Auth mirrors `app/admin/__init__.py` `AdminAuth`: login via
//! `UserService.authenticate_user`, JWT stored in the signed `session` cookie,
//! every non-auth `/admin` route redirects to `/admin/login` when
//! unauthenticated. On every write the `"blog"` response cache is invalidated
//! (port of `CacheClearingModelView`).
//!
//! The Python app throttles login attempts in-process; the Rust app is a
//! single process so throttling there is moot — intentionally not ported.

use std::collections::HashMap;
use std::sync::Arc;

use async_trait::async_trait;
use axum::extract::{Path, Query, State};
use axum::http::{header, HeaderMap, StatusCode};
use axum::response::{IntoResponse, Response};
use axum::Router;
use chrono::{DateTime, NaiveDateTime, Utc};
use domain::{
    Category, CategoryRepository, Icon, IconRepository, Post, PostRepository, Tag, TagRepository,
    User, UserRepository,
};
use minijinja::context;
use serde::Serialize;
use serde_json::Value as JsonValue;

use crate::app::AppState;
use crate::auth;
use crate::cache;
use crate::services::{UserService, WebError};
use crate::templates::render;

/// Descriptor mirroring the sqladmin `ModelView` configuration in
/// `app/admin/__init__.py` (column lists, searchable/sortable fields,
/// form-excluded fields).
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

/// All model descriptors, in sqladmin registration order.
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

fn get(form: &HashMap<String, String>, key: &str) -> String {
    form.get(key).cloned().unwrap_or_default()
}

fn checkbox(form: &HashMap<String, String>, key: &str) -> bool {
    form.get(key).map(|v| v == "on").unwrap_or(false)
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

/// Parse a datetime from the form. Empty → None. Accepts RFC3339
/// (`2026-01-01T12:00:00Z`) and naive `YYYY-MM-DDTHH:MM[:SS]` (assumed UTC).
fn parse_datetime_field(s: &str) -> Option<DateTime<Utc>> {
    let s = s.trim();
    if s.is_empty() {
        return None;
    }
    if let Ok(dt) = DateTime::parse_from_rfc3339(s) {
        return Some(dt.with_timezone(&Utc));
    }
    for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"] {
        if let Ok(naive) = NaiveDateTime::parse_from_str(s, fmt) {
            return Some(naive.and_utc());
        }
    }
    None
}

fn hash_form_password(password: &str) -> Result<String, WebError> {
    domain::security::hash_password(password)
        .map_err(|e| WebError::Internal(format!("password hashing failed: {e}")))
}

// ---------------------------------------------------------------------------
// Per-model stores
// ---------------------------------------------------------------------------

pub struct PostStore {
    repo: Arc<dyn PostRepository>,
    tags: Arc<dyn TagRepository>,
    categories: Arc<dyn CategoryRepository>,
}

impl PostStore {
    /// Parse the comma-joined tag ids submitted by the hidden `tags` input
    /// (maintained by admin.js from the checkbox chips).
    fn tag_ids(form: &HashMap<String, String>) -> Vec<i32> {
        get(form, "tags")
            .split(',')
            .filter_map(|s| s.trim().parse::<i32>().ok())
            .collect()
    }
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
        let now = Utc::now();
        let post = Post {
            id: None,
            pagetitle: get(form, "pagetitle"),
            alias: get(form, "alias"),
            content: get(form, "content"),
            createdon: Some(now),
            publishedon: parse_datetime_field(&get(form, "publishedon")),
            update_date: Some(now),
            category_id: get(form, "category_id").trim().parse().ok(),
            is_page: checkbox(form, "is_page"),
            user_id: None,
        };
        let created = self.repo.create(&post).await?;
        if let Some(id) = created.id {
            self.repo
                .set_tags_for_post(id, &Self::tag_ids(form))
                .await?;
        }
        Ok(())
    }

    async fn update_from_form(
        &self,
        id: i32,
        form: &HashMap<String, String>,
    ) -> Result<(), WebError> {
        let existing = self.repo.get_by_id(id).await?.ok_or(WebError::NotFound)?;
        let post = Post {
            id: Some(id),
            pagetitle: get(form, "pagetitle"),
            alias: get(form, "alias"),
            content: get(form, "content"),
            createdon: existing.createdon,
            publishedon: parse_datetime_field(&get(form, "publishedon")),
            // Bump the content version so cached pages re-render immediately.
            update_date: Some(Utc::now()),
            category_id: get(form, "category_id").trim().parse().ok(),
            is_page: checkbox(form, "is_page"),
            user_id: existing.user_id,
        };
        self.repo.update(&post).await?;
        self.repo
            .set_tags_for_post(id, &Self::tag_ids(form))
            .await?;
        Ok(())
    }

    async fn delete(&self, id: i32) -> Result<bool, WebError> {
        // `posts_tags` FKs have no ON DELETE action; clear the links first or
        // Postgres rejects the delete with an FK violation.
        self.repo.set_tags_for_post(id, &[]).await?;
        Ok(self.repo.delete(id).await?)
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
        let category = Category {
            id: None,
            title: get(form, "title"),
            alias: get(form, "alias"),
            template: if get(form, "template").is_empty() {
                None
            } else {
                Some(get(form, "template"))
            },
            page: if checkbox(form, "page") {
                Some(true)
            } else {
                None
            },
        };
        self.repo.create(&category).await?;
        Ok(())
    }

    async fn update_from_form(
        &self,
        id: i32,
        form: &HashMap<String, String>,
    ) -> Result<(), WebError> {
        let existing = self.repo.get_by_id(id).await?.ok_or(WebError::NotFound)?;
        let category = Category {
            id: Some(id),
            title: get(form, "title"),
            alias: get(form, "alias"),
            template: if get(form, "template").is_empty() {
                None
            } else {
                Some(get(form, "template"))
            },
            page: if checkbox(form, "page") {
                Some(true)
            } else {
                None
            },
        };
        let _ = existing;
        self.repo.update(&category).await?;
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
        let tag = Tag {
            id: None,
            title: get(form, "title"),
            alias: get(form, "alias"),
        };
        self.repo.create(&tag).await?;
        Ok(())
    }

    async fn update_from_form(
        &self,
        id: i32,
        form: &HashMap<String, String>,
    ) -> Result<(), WebError> {
        self.repo.get_by_id(id).await?.ok_or(WebError::NotFound)?;
        let tag = Tag {
            id: Some(id),
            title: get(form, "title"),
            alias: get(form, "alias"),
        };
        self.repo.update(&tag).await?;
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
        let hashed = hash_form_password(&get(form, "password"))?;
        let user = User {
            id: None,
            name: get(form, "name"),
            password: hashed,
            authenticated: checkbox(form, "authenticated"),
            createdon: Some(Utc::now()),
        };
        self.repo.create(&user).await?;
        Ok(())
    }

    async fn update_from_form(
        &self,
        id: i32,
        form: &HashMap<String, String>,
    ) -> Result<(), WebError> {
        let existing = self.repo.get_by_id(id).await?.ok_or(WebError::NotFound)?;
        let password = if get(form, "password").is_empty() {
            // Password field is form-excluded on edit; keep the stored hash.
            existing.password.clone()
        } else {
            hash_form_password(&get(form, "password"))?
        };
        let user = User {
            id: Some(id),
            name: get(form, "name"),
            password,
            authenticated: checkbox(form, "authenticated"),
            createdon: existing.createdon,
        };
        self.repo.update(&user).await?;
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
        let icon = Icon {
            id: None,
            title: get(form, "title"),
            url: get(form, "url"),
            content: if get(form, "content").is_empty() {
                None
            } else {
                Some(get(form, "content"))
            },
        };
        self.repo.create(&icon).await?;
        Ok(())
    }

    async fn update_from_form(
        &self,
        id: i32,
        form: &HashMap<String, String>,
    ) -> Result<(), WebError> {
        self.repo.get_by_id(id).await?.ok_or(WebError::NotFound)?;
        let icon = Icon {
            id: Some(id),
            title: get(form, "title"),
            url: get(form, "url"),
            content: if get(form, "content").is_empty() {
                None
            } else {
                Some(get(form, "content"))
            },
        };
        self.repo.update(&icon).await?;
        Ok(())
    }

    async fn delete(&self, id: i32) -> Result<bool, WebError> {
        Ok(self.repo.delete(id).await?)
    }
}

/// Build a store trait object for the given model name (accepts singular and
/// plural URL segments, like sqladmin's `/admin/posts/...`).
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
    auth::decode_token(&token)
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
    let username = get(&form, "username");
    let password = get(&form, "password");
    let user_service = UserService::new(state.users.clone());
    if let Some(user) = user_service.authenticate_user(&username, &password).await? {
        let token = auth::create_access_token(&user.name)
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

/// Re-render the create/edit form with the error message (like sqladmin's
/// flash), preserving the submitted field values. `NotFound` maps to a plain
/// 404 page.
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
        .route("/admin/", get(dashboard)) // sqladmin serves the index at /admin/
        .route("/admin/login", get(login_get).post(login_post))
        .route("/admin/logout", get(logout))
        .route("/admin/{model}", get(list))
        .route("/admin/{model}/", get(list))
        .route("/admin/{model}/create", get(create_form).post(create))
        .route("/admin/{model}/{id}/edit", get(edit_form).post(edit))
        .route("/admin/{model}/{id}/delete", get(delete).post(delete))
}
