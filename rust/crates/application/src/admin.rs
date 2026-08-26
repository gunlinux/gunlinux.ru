//! Admin write-path use cases: form → entity translation and persistence
//! orchestration for the admin panel. Each takes repository trait objects
//! and the raw form data and returns `()`, so the web layer only adapts
//! (HTTP ↔ forms ↔ templates). The rules that live here: post publishedon
//! parsing, the comma-joined tag ids, the `posts_tags` FK clear-before-delete,
//! the user password hash/blank-keeps-hash rule, and the nullable field
//! conventions for categories and icons.

use std::collections::HashMap;

use chrono::{DateTime, NaiveDateTime, Utc};
use domain::{
    security::hash_password, Category, CategoryRepository, Icon, IconRepository, Post,
    PostRepository, Tag, TagRepository, User, UserRepository,
};

use crate::error::AppError;

fn get(form: &HashMap<String, String>, key: &str) -> String {
    form.get(key).cloned().unwrap_or_default()
}

fn checkbox(form: &HashMap<String, String>, key: &str) -> bool {
    form.get(key).map(|v| v == "on").unwrap_or(false)
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

/// Parse the comma-joined tag ids submitted by the hidden `tags` input
/// (maintained by admin.js from the checkbox chips).
fn tag_ids(form: &HashMap<String, String>) -> Vec<i32> {
    get(form, "tags")
        .split(',')
        .filter_map(|s| s.trim().parse::<i32>().ok())
        .collect()
}

fn hash_form_password(password: &str) -> Result<String, AppError> {
    hash_password(password).map_err(|e| AppError::Internal(format!("password hashing failed: {e}")))
}

// ---------------------------------------------------------------------------
// Posts
// ---------------------------------------------------------------------------

pub async fn create_post(
    posts: &dyn PostRepository,
    form: &HashMap<String, String>,
) -> Result<(), AppError> {
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
    let created = posts.create(&post).await?;
    if let Some(id) = created.id {
        posts.set_tags_for_post(id, &tag_ids(form)).await?;
    }
    Ok(())
}

pub async fn update_post(
    posts: &dyn PostRepository,
    id: i32,
    form: &HashMap<String, String>,
) -> Result<(), AppError> {
    let existing = posts.get_by_id(id).await?.ok_or(AppError::NotFound)?;
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
    posts.update(&post).await?;
    posts.set_tags_for_post(id, &tag_ids(form)).await?;
    Ok(())
}

/// Delete a post. `posts_tags` FKs have no ON DELETE action; clear the links
/// first or Postgres rejects the delete with an FK violation.
pub async fn delete_post(posts: &dyn PostRepository, id: i32) -> Result<bool, AppError> {
    posts.set_tags_for_post(id, &[]).await?;
    Ok(posts.delete(id).await?)
}

// ---------------------------------------------------------------------------
// Categories
// ---------------------------------------------------------------------------

fn category_from_form(id: Option<i32>, form: &HashMap<String, String>) -> Category {
    let template = get(form, "template");
    Category {
        id,
        title: get(form, "title"),
        alias: get(form, "alias"),
        template: if template.is_empty() {
            None
        } else {
            Some(template)
        },
        page: if checkbox(form, "page") {
            Some(true)
        } else {
            None
        },
    }
}

pub async fn create_category(
    categories: &dyn CategoryRepository,
    form: &HashMap<String, String>,
) -> Result<(), AppError> {
    categories.create(&category_from_form(None, form)).await?;
    Ok(())
}

pub async fn update_category(
    categories: &dyn CategoryRepository,
    id: i32,
    form: &HashMap<String, String>,
) -> Result<(), AppError> {
    categories.get_by_id(id).await?.ok_or(AppError::NotFound)?;
    categories
        .update(&category_from_form(Some(id), form))
        .await?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Tags
// ---------------------------------------------------------------------------

fn tag_from_form(id: Option<i32>, form: &HashMap<String, String>) -> Tag {
    Tag {
        id,
        title: get(form, "title"),
        alias: get(form, "alias"),
    }
}

pub async fn create_tag(
    tags: &dyn TagRepository,
    form: &HashMap<String, String>,
) -> Result<(), AppError> {
    tags.create(&tag_from_form(None, form)).await?;
    Ok(())
}

pub async fn update_tag(
    tags: &dyn TagRepository,
    id: i32,
    form: &HashMap<String, String>,
) -> Result<(), AppError> {
    tags.get_by_id(id).await?.ok_or(AppError::NotFound)?;
    tags.update(&tag_from_form(Some(id), form)).await?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------

pub async fn create_user(
    users: &dyn UserRepository,
    form: &HashMap<String, String>,
) -> Result<(), AppError> {
    let user = User {
        id: None,
        name: get(form, "name"),
        password: hash_form_password(&get(form, "password"))?,
        authenticated: checkbox(form, "authenticated"),
        createdon: Some(Utc::now()),
    };
    users.create(&user).await?;
    Ok(())
}

pub async fn update_user(
    users: &dyn UserRepository,
    id: i32,
    form: &HashMap<String, String>,
) -> Result<(), AppError> {
    let existing = users.get_by_id(id).await?.ok_or(AppError::NotFound)?;
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
    users.update(&user).await?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Icons
// ---------------------------------------------------------------------------

fn icon_from_form(id: Option<i32>, form: &HashMap<String, String>) -> Icon {
    let content = get(form, "content");
    Icon {
        id,
        title: get(form, "title"),
        url: get(form, "url"),
        content: if content.is_empty() {
            None
        } else {
            Some(content)
        },
    }
}

pub async fn create_icon(
    icons: &dyn IconRepository,
    form: &HashMap<String, String>,
) -> Result<(), AppError> {
    icons.create(&icon_from_form(None, form)).await?;
    Ok(())
}

pub async fn update_icon(
    icons: &dyn IconRepository,
    id: i32,
    form: &HashMap<String, String>,
) -> Result<(), AppError> {
    icons.get_by_id(id).await?.ok_or(AppError::NotFound)?;
    icons.update(&icon_from_form(Some(id), form)).await?;
    Ok(())
}
