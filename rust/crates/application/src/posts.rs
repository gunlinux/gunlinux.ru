//! Read-path use cases: resolving the pages and listings the public site
//! renders. Each takes repository trait objects and plain inputs and returns
//! domain results, so the rules are exercisable without an HTTP stack.

use domain::{group_posts_by_year, Post, PostRepository, Tag, TagRepository, YearGroup};

use crate::error::AppError;

/// The nav pages for the layout: every post flagged as a page. (The
/// htmx-vs-full decision is an adapter concern and stays in `web`.)
pub async fn nav_pages(posts: &dyn PostRepository) -> Result<Vec<Post>, AppError> {
    Ok(posts.get_page_posts().await?)
}

/// All published content grouped by publication year (years descending) for
/// the index/posts listings.
pub async fn posts_by_year(posts: &dyn PostRepository) -> Result<Vec<YearGroup>, AppError> {
    let all = posts.get_all_published_content().await?;
    Ok(group_posts_by_year(all))
}

/// The published posts feed (RSS) and sitemap listing.
pub async fn published_posts(posts: &dyn PostRepository) -> Result<Vec<Post>, AppError> {
    Ok(posts.get_published_posts().await?)
}

/// The page posts (sitemap).
pub async fn page_posts(posts: &dyn PostRepository) -> Result<Vec<Post>, AppError> {
    Ok(posts.get_page_posts().await?)
}

/// Resolve a post view: the post with the given alias plus its tags.
/// `None` when the alias is unknown, or when the post is neither published
/// nor a page — drafts must not be reachable at their URL.
pub async fn resolve_post_view(
    posts: &dyn PostRepository,
    alias: &str,
) -> Result<Option<(Post, Vec<Tag>)>, AppError> {
    let Some(post) = posts.get_by_alias(alias).await? else {
        return Ok(None);
    };
    if !(post.is_published() || post.is_page) {
        return Ok(None);
    }
    let tags = match post.id {
        Some(id) => posts.get_tags_for_post(id).await?,
        None => Vec::new(),
    };
    Ok(Some((post, tags)))
}

/// Resolve a tag view: the tag with the given alias plus its posts.
/// `None` for unknown tags. Note the faithful quirk is preserved here:
/// drafts leak into tag listings (matching the pre-rewrite behavior).
pub async fn resolve_tag_view(
    tags: &dyn TagRepository,
    posts: &dyn PostRepository,
    alias: &str,
) -> Result<Option<(Tag, Vec<Post>)>, AppError> {
    let Some(tag) = tags.get_by_alias(alias).await? else {
        return Ok(None);
    };
    let tag_posts = match tag.id {
        Some(id) => posts.get_posts_by_tag(id).await?,
        None => Vec::new(),
    };
    Ok(Some((tag, tag_posts)))
}
