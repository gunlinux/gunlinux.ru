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

/// Mirrors `app/domain/post.py` `Post` dataclass.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Post {
    pub id: Option<i32>,
    pub pagetitle: String,
    pub alias: String,
    pub content: String,
    pub createdon: Option<DateTime<Utc>>,
    pub publishedon: Option<DateTime<Utc>>,
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
