use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// Render markdown to HTML, matching the Python app's behavior:
/// `markdown.markdown(content, extensions=["markdown.extensions.fenced_code"])`.
/// Raw HTML is passed through unsanitized (admin-authored content is trusted).
pub fn render_markdown(src: &str) -> String {
    let mut options = comrak::Options::default();
    // Disable GFM extras that python-markdown (without extensions) would not
    // produce, so existing content keeps its current rendering.
    options.extension.strikethrough = false;
    options.extension.table = false;
    options.extension.tasklist = false;
    options.extension.autolink = false;
    options.extension.tagfilter = false;
    options.extension.superscript = false;
    options.extension.footnotes = false;
    options.extension.description_lists = false;
    options.render.unsafe_ = true;
    options.render.hardbreaks = false;
    comrak::markdown_to_html(src, &options)
}

/// Render markdown for the `POST /md/` admin preview, matching the Python
/// route's plain `markdown.markdown(data)` call (NO extensions). python-markdown
/// without `fenced_code` renders fenced blocks as inline `<code>` spans inside a
/// `<p>` (language tag first, then a newline, then the content) instead of
/// `<pre><code>`. comrak 0.30 always parses fences (core CommonMark), so the
/// rendered `<pre><code>` blocks are converted back to that inline form. The
/// residual difference vs python-markdown (blank line after raw-HTML blocks
/// before lists) is documented in MIGRATION_CONTRACT.md.
pub fn render_markdown_preview(src: &str) -> String {
    let mut options = comrak::Options::default();
    options.extension.strikethrough = false;
    options.extension.table = false;
    options.extension.tasklist = false;
    options.extension.autolink = false;
    options.extension.tagfilter = false;
    options.extension.superscript = false;
    options.extension.footnotes = false;
    options.extension.description_lists = false;
    options.render.unsafe_ = true;
    options.render.hardbreaks = false;
    let html = comrak::markdown_to_html(src, &options);
    let html = python_md_code_spans(&html);
    // python-markdown never emits a trailing newline; comrak always does.
    html.trim_end().to_string()
}

/// Convert comrak `<pre><code class="language-X">content\n</code></pre>` blocks
/// into python-markdown's inline form `<p><code>X\ncontent</code></p>`, and
/// unescape `&quot;` inside the code content (python-markdown does not escape
/// quotes in code spans; comrak does).
fn python_md_code_spans(html: &str) -> String {
    const OPEN: &str = "<pre><code";
    const CLOSE: &str = "</code></pre>";
    let mut out = String::with_capacity(html.len());
    let mut rest = html;
    loop {
        let Some(start) = rest.find(OPEN) else {
            out.push_str(rest);
            break;
        };
        let after = &rest[start..];
        // The opening tag is `<pre><code...>`; its end `>` is the first one
        // AFTER the `<pre><code` prefix (not the one closing `<pre>`).
        let Some(tag_end_rel) = after[OPEN.len()..].find('>') else {
            out.push_str(rest);
            break;
        };
        let tag_end = tag_end_rel + OPEN.len();
        let open_tag = &after[..=tag_end];
        let Some(close) = after.find(CLOSE) else {
            out.push_str(rest);
            break;
        };
        out.push_str(&rest[..start]);
        let content = after[tag_end + 1..close]
            .strip_suffix('\n')
            .unwrap_or(&after[tag_end + 1..close]);
        let lang = open_tag
            .split("language-")
            .nth(1)
            .and_then(|s| s.split('"').next())
            .unwrap_or("");
        out.push_str("<p><code>");
        if !lang.is_empty() {
            out.push_str(lang);
            out.push('\n');
        }
        out.push_str(&content.replace("&quot;", "\""));
        out.push_str("</code></p>");
        rest = &after[close + CLOSE.len()..];
    }
    out
}

/// Mirrors `app/domain/post.py` `Post` dataclass. `update_date` is a
/// post-migration addition (cache content versioning): set on create/update
/// by the admin layer, `NULL` for legacy rows.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Post {
    pub id: Option<i32>,
    pub pagetitle: String,
    pub alias: String,
    pub content: String,
    pub createdon: Option<DateTime<Utc>>,
    pub publishedon: Option<DateTime<Utc>>,
    #[serde(default)]
    pub update_date: Option<DateTime<Utc>>,
    pub category_id: Option<i32>,
    pub is_page: bool,
    pub user_id: Option<i32>,
}

impl Post {
    pub fn new(
        pagetitle: impl Into<String>,
        alias: impl Into<String>,
        content: impl Into<String>,
    ) -> Self {
        Self {
            id: None,
            pagetitle: pagetitle.into(),
            alias: alias.into(),
            content: content.into(),
            createdon: Some(Utc::now()),
            publishedon: None,
            update_date: Some(Utc::now()),
            category_id: None,
            is_page: false,
            user_id: None,
        }
    }

    pub fn is_published(&self) -> bool {
        self.publishedon.is_some()
    }

    pub fn markdown(&self) -> String {
        render_markdown(&self.content)
    }

    /// Short plain-text excerpt (first paragraph, capped at 300 chars) for RSS.
    /// Ported 1:1 from the Python `Post.teaser` property — operates on raw
    /// content, no markdown rendering or HTML stripping.
    pub fn teaser(&self) -> String {
        let first = self
            .content
            .trim()
            .split("\n\n")
            .next()
            .unwrap_or("")
            .trim();
        if first.chars().count() > 300 {
            let mut truncated: String = first.chars().take(300).collect();
            while truncated
                .chars()
                .next_back()
                .is_some_and(char::is_whitespace)
            {
                truncated.pop();
            }
            truncated.push('…');
            truncated
        } else {
            first.to_string()
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn markdown_renders_fenced_code() {
        let html = render_markdown("```rust\nfn main() {}\n```");
        assert!(html.contains("<pre><code"));
        assert!(html.contains("fn main() {}"));
    }

    #[test]
    fn markdown_passes_raw_html_through() {
        let html = render_markdown("<div class=\"x\">hi</div>");
        assert!(html.contains("<div class=\"x\">hi</div>"));
    }

    #[test]
    fn preview_renders_fence_as_inline_code() {
        // python-markdown without fenced_code: ```rust block becomes an inline
        // <code> span in a <p>, language tag first, quotes left unescaped.
        let html = render_markdown_preview("```rust\nfn main() { println!(\"hi\"); }\n```");
        assert_eq!(
            html,
            "<p><code>rust\nfn main() { println!(\"hi\"); }</code></p>"
        );
    }

    #[test]
    fn preview_renders_fence_without_language() {
        let html = render_markdown_preview("```\nplain\n```");
        assert_eq!(html, "<p><code>plain</code></p>");
    }

    #[test]
    fn preview_keeps_normal_markdown() {
        let html = render_markdown_preview("# Title\n\nText with `code` and **bold**.");
        assert_eq!(
            html,
            "<h1>Title</h1>\n<p>Text with <code>code</code> and <strong>bold</strong>.</p>"
        );
    }

    #[test]
    fn teaser_takes_first_paragraph() {
        let post = Post::new("t", "a", "first paragraph.\n\nsecond paragraph.");
        assert_eq!(post.teaser(), "first paragraph.");
    }

    #[test]
    fn teaser_truncates_at_300() {
        let post = Post::new("t", "a", "x".repeat(500));
        let teaser = post.teaser();
        assert!(teaser.ends_with('…'));
        assert!(teaser.chars().count() <= 301);
    }

    #[test]
    fn teaser_does_not_truncate_short_text() {
        let post = Post::new("t", "a", "short");
        assert_eq!(post.teaser(), "short");
    }
}
