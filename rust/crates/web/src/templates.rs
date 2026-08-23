//! Minijinja template environment, built from the templates embedded at
//! compile time via `include_dir` (mirrors `app/core/templates.py`).
//!
//! All 16 templates from `app/templates/` are vendored under `templates/`
//! (same directory structure). The `settings` global is registered so
//! templates can access `settings.yandex_verification` / `settings.yandex_metrika`.

use std::sync::Arc;

use chrono::{DateTime, Datelike, Timelike, Utc};
use domain::Post;
use include_dir::{include_dir, Dir};
use minijinja::{Environment, UndefinedBehavior, Value};
use serde::Serialize;

use crate::settings::Settings;

static TEMPLATES_DIR: Dir = include_dir!("$CARGO_MANIFEST_DIR/templates");

/// View wrapper around `Post` that exposes the pre-rendered `markdown` HTML as
/// a template field, so `{{ post.markdown|safe }}` works without Minijinja
/// calling methods (Jinja2 calls the `markdown` property).
#[derive(Debug, Clone, Serialize)]
pub struct PostView {
    #[serde(flatten)]
    pub post: Post,
    pub markdown: String,
}

impl PostView {
    pub fn new(post: Post) -> Self {
        let markdown = post.markdown();
        Self { post, markdown }
    }
}

/// A year group for the posts listing. Replaces the Jinja2
/// `posts|selectattr('publishedon')|groupby('publishedon.year')|sort(reverse=True)`
/// chain, which Minijinja cannot evaluate — the handler precomputes the groups.
#[derive(Debug, Clone, Serialize)]
pub struct YearGroup {
    pub year: i32,
    pub posts: Vec<Post>,
}

/// Group published posts by publication year, years descending (posts keep
/// their input order inside each group — the repository already returns them
/// `publishedon DESC`).
pub fn group_posts_by_year(posts: Vec<Post>) -> Vec<YearGroup> {
    let mut groups: Vec<YearGroup> = Vec::new();
    for post in posts {
        let Some(publishedon) = post.publishedon else {
            continue;
        };
        let year = publishedon.year();
        match groups.iter_mut().find(|g| g.year == year) {
            Some(g) => g.posts.push(post),
            None => groups.push(YearGroup {
                year,
                posts: vec![post],
            }),
        }
    }
    groups.sort_by_key(|g| std::cmp::Reverse(g.year));
    groups
}

const WEEKDAYS_SHORT: [&str; 7] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const MONTHS_SHORT: [&str; 12] = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];
const MONTHS_FULL: [&str; 12] = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
];

/// Minimal Python-style `strftime` supporting the directives the templates use:
/// `%a %b %B %d %Y %H %M %S %z`. Dates are normalized to UTC before formatting
/// and `%z` always renders the RFC822-style `+0000` (matching the expected
/// `Thu, 01 Jan 2026 00:00:00 +0000` output).
fn python_strftime(dt: &DateTime<Utc>, fmt: &str) -> String {
    let mut out = String::new();
    let mut chars = fmt.chars().peekable();
    while let Some(c) = chars.next() {
        if c != '%' {
            out.push(c);
            continue;
        }
        match chars.next() {
            Some('a') => out.push_str(WEEKDAYS_SHORT[dt.weekday().num_days_from_monday() as usize]),
            Some('b') => out.push_str(MONTHS_SHORT[(dt.month() - 1) as usize]),
            Some('B') => out.push_str(MONTHS_FULL[(dt.month() - 1) as usize]),
            Some('d') => out.push_str(&format!("{:02}", dt.day())),
            Some('Y') => out.push_str(&format!("{}", dt.year())),
            Some('H') => out.push_str(&format!("{:02}", dt.hour())),
            Some('M') => out.push_str(&format!("{:02}", dt.minute())),
            Some('S') => out.push_str(&format!("{:02}", dt.second())),
            Some('z') => out.push_str("+0000"),
            Some(other) => {
                out.push('%');
                out.push(other);
            }
            None => out.push('%'),
        }
    }
    out
}

/// Minijinja filter: `{{ value|strftime("%B %d, %Y") }}`.
///
/// Values arrive as RFC3339 strings (how chrono `DateTime<Utc>` serializes
/// through serde). `None`/empty → empty string.
fn strftime_filter(value: Value, fmt: Option<&str>) -> Result<String, minijinja::Error> {
    let fmt = fmt.unwrap_or("%a %b %d %H:%M:%S %Y");
    let Some(s) = value.as_str() else {
        return Ok(String::new());
    };
    if s.is_empty() {
        return Ok(String::new());
    }
    let dt = DateTime::parse_from_rfc3339(s).map_err(|e| {
        minijinja::Error::new(
            minijinja::ErrorKind::InvalidOperation,
            format!("strftime: cannot parse datetime {s:?}: {e}"),
        )
    })?;
    Ok(python_strftime(&dt.to_utc(), fmt))
}

/// Minijinja filter: `{{ post.content|teaser }}` — the first paragraph of the
/// content, capped at 300 chars (delegates to the domain `Post::teaser`).
fn teaser_filter(value: Value) -> Result<String, minijinja::Error> {
    let src = value.as_str().unwrap_or("");
    let post = Post::new("", "", src);
    Ok(post.teaser())
}

/// Build the template environment: registers every embedded template, the
/// `strftime`/`teaser` filters, and the global `settings` value.
pub fn build_env(settings: Arc<Settings>) -> Environment<'static> {
    let mut env = Environment::new();
    // `{% for x in undefined %}` must render nothing (footer `icons` is only
    // filled by htmx) and `{% if undefined %}` must be falsy — Chainable does
    // both while also allowing chained lookups.
    env.set_undefined_behavior(UndefinedBehavior::Chainable);
    env.add_filter("strftime", strftime_filter);
    env.add_filter("teaser", teaser_filter);
    for file in template_files(&TEMPLATES_DIR) {
        let name = file.path().to_str().expect("template path is utf-8");
        let source = file
            .contents_utf8()
            .unwrap_or_else(|| panic!("template {name} is not utf-8"));
        env.add_template_owned(name, source)
            .unwrap_or_else(|e| panic!("template {name} failed to compile: {e}"));
    }
    env.add_global("settings", Value::from_serialize(&*settings));
    env
}

/// `include_dir::Dir::files()` is non-recursive — collect every file across
/// the subdirectories (`snippets/`, `icons/`, `sqladmin/`, `admin/`).
fn template_files<'a>(dir: &'a Dir<'a>) -> Vec<&'a include_dir::File<'a>> {
    let mut out: Vec<&include_dir::File> = dir.files().collect();
    for sub in dir.dirs() {
        out.extend(template_files(sub));
    }
    out
}

/// Render a template with the given context.
pub fn render(
    env: &Environment<'static>,
    name: &str,
    ctx: impl Serialize,
) -> Result<String, crate::WebError> {
    let template = env
        .get_template(name)
        .map_err(|e| crate::WebError::Internal(format!("template {name}: {e}")))?;
    template
        .render(ctx)
        .map_err(|e| crate::WebError::Internal(format!("render {name}: {e}")))
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::TimeZone;
    use minijinja::context;

    #[test]
    fn strftime_formats_like_python() {
        let dt = Utc.with_ymd_and_hms(2026, 1, 1, 0, 0, 0).unwrap();
        assert_eq!(
            python_strftime(&dt, "%a, %d %b %Y %H:%M:%S %z"),
            "Thu, 01 Jan 2026 00:00:00 +0000"
        );
        assert_eq!(python_strftime(&dt, "%B %d, %Y"), "January 01, 2026");
    }

    #[test]
    fn groups_posts_by_year_desc() {
        let now = Utc::now();
        let p2024 = Post {
            publishedon: Some(now.with_year(2024).unwrap()),
            ..Post::new("a", "a", "x")
        };
        let p2026a = Post {
            publishedon: Some(now.with_year(2026).unwrap()),
            ..Post::new("b", "b", "x")
        };
        let p2026b = Post {
            publishedon: Some(now.with_year(2026).unwrap()),
            ..Post::new("c", "c", "x")
        };
        let unpublished = Post::new("d", "d", "x");
        let groups = group_posts_by_year(vec![p2026a, unpublished, p2024, p2026b]);
        assert_eq!(groups.len(), 2);
        assert_eq!(groups[0].year, 2026);
        assert_eq!(groups[0].posts.len(), 2);
        assert_eq!(groups[1].year, 2024);
    }

    #[test]
    fn environment_builds_and_renders_index() {
        let settings = Arc::new(Settings::default());
        let env = build_env(settings);
        let out = render(&env, "index.html", context! {}).unwrap();
        assert!(out.contains("Неразумный перфекционизм"));
        assert!(out.contains("yandex</noscript>") || out.contains("mc.yandex.ru"));
    }

    #[test]
    fn undefined_loop_iterates_empty() {
        let settings = Arc::new(Settings::default());
        let env = build_env(settings);
        // footer.html iterates `icons` which is undefined on most pages.
        let out = render(&env, "footer.html", context! {}).unwrap();
        assert!(!out.contains("class=\"nav__link\""));
    }
}
