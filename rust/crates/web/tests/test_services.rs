//! Dedicated service-layer tests (port of `tests/test_services.py`).
//!
//! The five services are exercised directly through fake in-memory repositories
//! implementing the `domain` traits — no HTTP, no real DB. The fakes mirror the
//! semantics of the SeaORM-backed repos in `persistence`:
//!
//! - finders on a missing row return `Ok(None)` / an empty `Vec`;
//! - `create` on a duplicate unique key (alias/title) surfaces
//!   `RepoError::Conflict`, mirroring the DB unique-constraint → `translate_err`
//!   path; `users.name` has no unique constraint, so it is *not* checked;
//! - `update` of an id that does not exist returns `RepoError::NotFound`.

use std::sync::Arc;

use chrono::{Duration, Utc};
use domain::{Category, Icon, Post, RepoError, Repository, Tag, User};
use fakes::{FakeCategoryRepo, FakeIconRepo, FakePostRepo, FakeTagRepo, FakeUserRepo, SharedStore};
use web::services::{CategoryService, IconService, PostService, TagService, UserService};
use web::WebError;

// ---------------------------------------------------------------------------
// PostService
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_post_service_crud() {
    let svc = PostService::new(Arc::new(FakePostRepo::new(SharedStore::default())));

    let created = svc
        .create_post(&Post::new("Hello", "hello-svc", "world"))
        .await
        .unwrap();
    assert!(created.id.is_some());

    assert!(svc.get_post_by_alias("hello-svc").await.unwrap().is_some());
    assert!(svc
        .get_all_posts()
        .await
        .unwrap()
        .iter()
        .any(|p| p.alias == "hello-svc"));
}

#[tokio::test]
async fn test_get_post_by_alias_not_found() {
    let svc = PostService::new(Arc::new(FakePostRepo::new(SharedStore::default())));

    assert!(svc.get_post_by_alias("nope-svc").await.unwrap().is_none());
}

#[tokio::test]
async fn test_post_service_published() {
    let svc = PostService::new(Arc::new(FakePostRepo::new(SharedStore::default())));

    let mut post = Post::new("Pub", "pub-svc", "x");
    post.publishedon = Some(Utc::now());
    svc.create_post(&post).await.unwrap();

    assert!(svc
        .get_published_posts()
        .await
        .unwrap()
        .iter()
        .any(|p| p.alias == "pub-svc"));
}

#[tokio::test]
async fn test_published_posts_exclude_drafts() {
    let svc = PostService::new(Arc::new(FakePostRepo::new(SharedStore::default())));

    let mut published = Post::new("Live", "live-svc", "x");
    published.publishedon = Some(Utc::now());
    svc.create_post(&published).await.unwrap();
    // Draft: no `publishedon`.
    svc.create_post(&Post::new("Draft", "draft-svc", "secret"))
        .await
        .unwrap();

    let published = svc.get_published_posts().await.unwrap();
    let published_aliases: Vec<&str> = published.iter().map(|p| p.alias.as_str()).collect();
    assert_eq!(published_aliases, vec!["live-svc"]);

    let content = svc.get_all_published_content().await.unwrap();
    let content_aliases: Vec<&str> = content.iter().map(|p| p.alias.as_str()).collect();
    assert_eq!(content_aliases, vec!["live-svc"]);

    // The draft is still visible through the unfiltered listing.
    assert!(svc
        .get_all_posts()
        .await
        .unwrap()
        .iter()
        .any(|p| p.alias == "draft-svc"));
}

#[tokio::test]
async fn test_page_posts_are_not_blog_content() {
    let svc = PostService::new(Arc::new(FakePostRepo::new(SharedStore::default())));

    let mut page = Post::new("About", "about-svc", "page content");
    page.publishedon = Some(Utc::now());
    page.category_id = Some(1);
    page.is_page = true;
    svc.create_post(&page).await.unwrap();

    let mut post = Post::new("Blog", "blog-svc", "x");
    post.publishedon = Some(Utc::now());
    svc.create_post(&post).await.unwrap();

    // Page only appears in the page listing.
    let pages = svc.get_page_posts().await.unwrap();
    let page_aliases: Vec<&str> = pages.iter().map(|p| p.alias.as_str()).collect();
    assert_eq!(page_aliases, vec!["about-svc"]);

    // And is excluded from the blog content listings (it has a category).
    assert!(svc
        .get_all_published_content()
        .await
        .unwrap()
        .iter()
        .all(|p| p.alias != "about-svc"));
    assert!(svc
        .get_published_posts()
        .await
        .unwrap()
        .iter()
        .all(|p| p.alias != "about-svc"));
}

#[tokio::test]
async fn test_published_posts_ordered_newest_first() {
    let svc = PostService::new(Arc::new(FakePostRepo::new(SharedStore::default())));

    let mut older = Post::new("Older", "older-svc", "x");
    older.publishedon = Some(Utc::now() - Duration::hours(1));
    let mut newer = Post::new("Newer", "newer-svc", "x");
    newer.publishedon = Some(Utc::now());

    svc.create_post(&older).await.unwrap();
    svc.create_post(&newer).await.unwrap();

    // The real queries ORDER BY publishedon DESC.
    let published = svc.get_published_posts().await.unwrap();
    let aliases: Vec<&str> = published.iter().map(|p| p.alias.as_str()).collect();
    assert_eq!(aliases, vec!["newer-svc", "older-svc"]);
}

#[tokio::test]
async fn test_get_posts_by_tag() {
    let store = SharedStore::default();
    let svc = PostService::new(Arc::new(FakePostRepo::new(store.clone())));
    let tag_svc = TagService::new(Arc::new(FakeTagRepo::new(store.clone())));

    let tagged = svc
        .create_post(&Post::new("Tagged", "tagged-svc", "x"))
        .await
        .unwrap();
    // Drafts linked to a tag are returned too — the real query has no
    // published filter.
    let draft = svc
        .create_post(&Post::new("Tagged Draft", "tagged-draft-svc", "x"))
        .await
        .unwrap();
    svc.create_post(&Post::new("Untagged", "untagged-svc", "x"))
        .await
        .unwrap();
    let tag = tag_svc
        .create_tag(&Tag {
            id: None,
            title: "Rust".to_string(),
            alias: "rust-svc".to_string(),
        })
        .await
        .unwrap();
    {
        let mut store = store.lock().unwrap();
        store.post_tags.push((tagged.id.unwrap(), tag.id.unwrap()));
        store.post_tags.push((draft.id.unwrap(), tag.id.unwrap()));
    }

    let posts = svc.get_posts_by_tag(tag.id.unwrap()).await.unwrap();
    let aliases: Vec<&str> = posts.iter().map(|p| p.alias.as_str()).collect();
    assert_eq!(aliases, vec!["tagged-svc", "tagged-draft-svc"]);
    assert!(!aliases.contains(&"untagged-svc"));

    // Unknown tag id → empty, not an error.
    assert!(svc.get_posts_by_tag(999).await.unwrap().is_empty());
}

#[tokio::test]
async fn test_get_tags_for_post() {
    let store = SharedStore::default();
    let svc = PostService::new(Arc::new(FakePostRepo::new(store.clone())));
    let tag_svc = TagService::new(Arc::new(FakeTagRepo::new(store.clone())));

    let post = svc
        .create_post(&Post::new("Linked", "linked-svc", "x"))
        .await
        .unwrap();
    let other = svc
        .create_post(&Post::new("Other", "other-svc", "x"))
        .await
        .unwrap();
    let linked = tag_svc
        .create_tag(&Tag {
            id: None,
            title: "FastAPI".to_string(),
            alias: "fastapi-svc".to_string(),
        })
        .await
        .unwrap();
    let unrelated = tag_svc
        .create_tag(&Tag {
            id: None,
            title: "Other".to_string(),
            alias: "other-tag-svc".to_string(),
        })
        .await
        .unwrap();
    {
        let mut store = store.lock().unwrap();
        store.post_tags.push((post.id.unwrap(), linked.id.unwrap()));
    }

    let tags = svc.get_tags_for_post(post.id.unwrap()).await.unwrap();
    assert_eq!(tags.len(), 1);
    assert_eq!(tags[0].alias, "fastapi-svc");
    assert_eq!(tags[0].id, linked.id);
    assert!(!tags.iter().any(|t| t.id == unrelated.id));

    // A post with no tags → empty, not an error.
    assert!(svc
        .get_tags_for_post(other.id.unwrap())
        .await
        .unwrap()
        .is_empty());
}

#[tokio::test]
async fn test_create_post_duplicate_alias_conflict() {
    let svc = PostService::new(Arc::new(FakePostRepo::new(SharedStore::default())));

    svc.create_post(&Post::new("First", "dup-svc", "x"))
        .await
        .unwrap();
    let err = svc
        .create_post(&Post::new("Second", "dup-svc", "y"))
        .await
        .unwrap_err();
    assert!(matches!(err, WebError::Conflict(_)));
}

// ---------------------------------------------------------------------------
// TagService
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_tag_service_crud() {
    let svc = TagService::new(Arc::new(FakeTagRepo::new(SharedStore::default())));

    let created = svc
        .create_tag(&Tag {
            id: None,
            title: "FastAPI".to_string(),
            alias: "fastapi-svc".to_string(),
        })
        .await
        .unwrap();
    assert!(created.id.is_some());

    assert!(svc.get_tag_by_alias("fastapi-svc").await.unwrap().is_some());
}

#[tokio::test]
async fn test_get_tag_by_alias_not_found() {
    let svc = TagService::new(Arc::new(FakeTagRepo::new(SharedStore::default())));

    assert!(svc.get_tag_by_alias("nope-svc").await.unwrap().is_none());
}

#[tokio::test]
async fn test_create_tag_duplicate_alias_conflict() {
    let svc = TagService::new(Arc::new(FakeTagRepo::new(SharedStore::default())));

    svc.create_tag(&Tag {
        id: None,
        title: "First".to_string(),
        alias: "dup-tag-svc".to_string(),
    })
    .await
    .unwrap();
    let err = svc
        .create_tag(&Tag {
            id: None,
            title: "Second".to_string(),
            alias: "dup-tag-svc".to_string(),
        })
        .await
        .unwrap_err();
    assert!(matches!(err, WebError::Conflict(_)));
}

// ---------------------------------------------------------------------------
// UserService
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_user_service_auth() {
    let svc = UserService::new(Arc::new(FakeUserRepo::new(SharedStore::default())));

    let hashed = domain::security::hash_password("pass").unwrap();
    let created = svc
        .create_user(&User::new("svcauth", hashed))
        .await
        .unwrap();
    assert!(created.id.is_some());

    // Correct password → the user; wrong password → None (mirrors Python,
    // where authentication failure is a None return, not an exception).
    assert!(svc
        .authenticate_user("svcauth", "pass")
        .await
        .unwrap()
        .is_some());
    assert!(svc
        .authenticate_user("svcauth", "bad")
        .await
        .unwrap()
        .is_none());
}

#[tokio::test]
async fn test_authenticate_unknown_user_returns_none() {
    let svc = UserService::new(Arc::new(FakeUserRepo::new(SharedStore::default())));

    assert!(svc
        .authenticate_user("ghost", "whatever")
        .await
        .unwrap()
        .is_none());
}

// ---------------------------------------------------------------------------
// CategoryService
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_category_service_crud() {
    let svc = CategoryService::new(Arc::new(FakeCategoryRepo::new(SharedStore::default())));

    let created = svc
        .create_category(&Category {
            id: None,
            title: "Pages".to_string(),
            alias: "pages-svc".to_string(),
            template: None,
            page: Some(true),
        })
        .await
        .unwrap();
    assert!(created.id.is_some());

    let found = svc
        .get_category_by_alias("pages-svc")
        .await
        .unwrap()
        .unwrap();
    assert_eq!(found.page, Some(true));
}

#[tokio::test]
async fn test_create_category_duplicate_alias_conflict() {
    let svc = CategoryService::new(Arc::new(FakeCategoryRepo::new(SharedStore::default())));

    svc.create_category(&Category {
        id: None,
        title: "Pages".to_string(),
        alias: "pages-dup-svc".to_string(),
        template: None,
        page: Some(true),
    })
    .await
    .unwrap();
    let err = svc
        .create_category(&Category {
            id: None,
            title: "Pages 2".to_string(),
            alias: "pages-dup-svc".to_string(),
            template: None,
            page: None,
        })
        .await
        .unwrap_err();
    assert!(matches!(err, WebError::Conflict(_)));
}

// ---------------------------------------------------------------------------
// IconService
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_icon_service_crud() {
    let svc = IconService::new(Arc::new(FakeIconRepo::new(SharedStore::default())));

    let created = svc
        .create_icon(&Icon {
            id: None,
            title: "Twitter-svc".to_string(),
            url: "https://twitter.com/svc".to_string(),
            content: Some("<svg/>".to_string()),
        })
        .await
        .unwrap();
    assert!(created.id.is_some());

    assert!(svc
        .get_icon_by_title("Twitter-svc")
        .await
        .unwrap()
        .is_some());
    assert!(!svc.get_all_icons().await.unwrap().is_empty());
}

#[tokio::test]
async fn test_create_icon_duplicate_title_conflict() {
    let svc = IconService::new(Arc::new(FakeIconRepo::new(SharedStore::default())));

    svc.create_icon(&Icon {
        id: None,
        title: "dup-icon-svc".to_string(),
        url: "https://example.com/1".to_string(),
        content: None,
    })
    .await
    .unwrap();
    let err = svc
        .create_icon(&Icon {
            id: None,
            title: "dup-icon-svc".to_string(),
            url: "https://example.com/2".to_string(),
            content: None,
        })
        .await
        .unwrap_err();
    assert!(matches!(err, WebError::Conflict(_)));
}

// ---------------------------------------------------------------------------
// Error mapping and fake-repo semantics
// ---------------------------------------------------------------------------

/// Services are thin pass-throughs: the only error path from a service call is
/// `RepoError` propagated through `From<RepoError> for WebError` via `?`. Pin
/// that mapping directly.
#[test]
fn test_repo_error_to_web_error_mapping() {
    assert!(matches!(
        WebError::from(RepoError::NotFound),
        WebError::NotFound
    ));
    assert!(matches!(
        WebError::from(RepoError::Conflict("dup".to_string())),
        WebError::Conflict(_)
    ));
    assert!(matches!(
        WebError::from(RepoError::Db("boom".to_string())),
        WebError::Internal(_)
    ));
}

/// The real repos return `RepoError::NotFound` when updating/deleting an
/// entity that is not in the store; the fakes mirror that.
#[tokio::test]
async fn test_update_missing_entity_returns_not_found() {
    let repo = FakePostRepo::new(SharedStore::default());

    // No id yet → nothing to update.
    let err = repo
        .update(&Post::new("Ghost", "ghost-svc", "x"))
        .await
        .unwrap_err();
    assert!(matches!(err, RepoError::NotFound));

    // An id that was never assigned is equally missing.
    let ghost = Post {
        id: Some(999),
        ..Post::new("Ghost", "ghost-svc", "x")
    };
    let err = repo.update(&ghost).await.unwrap_err();
    assert!(matches!(err, RepoError::NotFound));
}

#[tokio::test]
async fn test_delete_missing_entity_returns_false() {
    let repo = FakePostRepo::new(SharedStore::default());

    assert!(!repo.delete(999).await.unwrap());

    let created = repo
        .create(&Post::new("Here", "here-svc", "x"))
        .await
        .unwrap();
    assert!(repo.delete(created.id.unwrap()).await.unwrap());
    assert!(!repo.delete(created.id.unwrap()).await.unwrap());
}

// ---------------------------------------------------------------------------
// In-memory fake repositories
// ---------------------------------------------------------------------------

/// Fake repos implementing the `domain` traits with the semantics of the real
/// SeaORM-backed repositories (see `persistence/src/repositories`):
///
/// - `get_by_alias` / `get_by_title` / `get_by_name` / `authenticate` return
///   `Ok(None)` for unknown rows;
/// - `create` rejects duplicate unique keys (`posts.alias`, `tags.alias`,
///   `categories.alias`, `icons.title`/`icons.url`) with `RepoError::Conflict`
///   — the in-memory analogue of the DB unique constraint surfacing through
///   `translate_err`. `users.name` has no unique constraint in the schema, so
///   it is not checked;
/// - `update` of a missing id returns `RepoError::NotFound`;
/// - `delete` of a missing id returns `Ok(false)`.
mod fakes {
    use std::sync::{Arc, Mutex};

    use async_trait::async_trait;
    use chrono::{DateTime, Utc};
    use domain::{
        Category, CategoryRepository, Icon, IconRepository, Post, PostRepository, RepoError,
        Repository, Tag, TagRepository, User, UserRepository,
    };

    /// All fake state in one lockable store (one store per test).
    #[derive(Default)]
    pub struct Store {
        pub posts: Vec<Post>,
        pub tags: Vec<Tag>,
        /// (post_id, tag_id) associations for the posts_tags m2m.
        pub post_tags: Vec<(i32, i32)>,
        pub users: Vec<User>,
        pub categories: Vec<Category>,
        pub icons: Vec<Icon>,
        pub next_id: i32,
    }

    pub type SharedStore = Arc<Mutex<Store>>;

    fn next_id(store: &mut Store) -> i32 {
        store.next_id += 1;
        store.next_id
    }

    // -----------------------------------------------------------------------
    // Posts
    // -----------------------------------------------------------------------

    pub struct FakePostRepo {
        store: SharedStore,
    }

    impl FakePostRepo {
        pub fn new(store: SharedStore) -> Self {
            Self { store }
        }
    }

    #[async_trait]
    impl Repository<Post, i32> for FakePostRepo {
        async fn get_by_id(&self, id: i32) -> Result<Option<Post>, RepoError> {
            let store = self.store.lock().unwrap();
            Ok(store.posts.iter().find(|p| p.id == Some(id)).cloned())
        }

        async fn get_all(&self) -> Result<Vec<Post>, RepoError> {
            let store = self.store.lock().unwrap();
            Ok(store.posts.clone())
        }

        async fn create(&self, entity: &Post) -> Result<Post, RepoError> {
            let mut store = self.store.lock().unwrap();
            if store.posts.iter().any(|p| p.alias == entity.alias) {
                return Err(RepoError::Conflict(format!(
                    "duplicate key value violates unique constraint on posts.alias: {}",
                    entity.alias
                )));
            }
            let id = next_id(&mut store);
            let mut post = entity.clone();
            post.id = Some(id);
            store.posts.push(post.clone());
            Ok(post)
        }

        async fn update(&self, entity: &Post) -> Result<Post, RepoError> {
            let mut store = self.store.lock().unwrap();
            let Some(idx) = store.posts.iter().position(|p| p.id == entity.id) else {
                return Err(RepoError::NotFound);
            };
            store.posts[idx] = entity.clone();
            Ok(entity.clone())
        }

        async fn delete(&self, id: i32) -> Result<bool, RepoError> {
            let mut store = self.store.lock().unwrap();
            let before = store.posts.len();
            store.posts.retain(|p| p.id != Some(id));
            Ok(store.posts.len() != before)
        }
    }

    #[async_trait]
    impl PostRepository for FakePostRepo {
        async fn get_by_alias(&self, alias: &str) -> Result<Option<Post>, RepoError> {
            let store = self.store.lock().unwrap();
            Ok(store.posts.iter().find(|p| p.alias == alias).cloned())
        }

        /// `publishedon IS NOT NULL AND category_id IS NULL`, ordered by
        /// `publishedon` DESC (mirrors the real query).
        async fn get_published_posts(&self) -> Result<Vec<Post>, RepoError> {
            let store = self.store.lock().unwrap();
            let mut posts: Vec<Post> = store
                .posts
                .iter()
                .filter(|p| p.publishedon.is_some() && p.category_id.is_none())
                .cloned()
                .collect();
            posts.sort_by_key(|p| std::cmp::Reverse(p.publishedon));
            Ok(posts)
        }

        /// `publishedon IS NOT NULL AND NOT page` (uncategorised posts
        /// included), ordered by `publishedon` DESC.
        async fn get_all_published_content(&self) -> Result<Vec<Post>, RepoError> {
            let store = self.store.lock().unwrap();
            let mut posts: Vec<Post> = store
                .posts
                .iter()
                .filter(|p| p.publishedon.is_some() && !p.is_page)
                .cloned()
                .collect();
            posts.sort_by_key(|p| std::cmp::Reverse(p.publishedon));
            Ok(posts)
        }

        /// Posts whose category has `page = TRUE` (domain: `is_page`).
        async fn get_page_posts(&self) -> Result<Vec<Post>, RepoError> {
            let store = self.store.lock().unwrap();
            Ok(store.posts.iter().filter(|p| p.is_page).cloned().collect())
        }

        /// Posts linked to the tag via `posts_tags` — no published filter,
        /// mirroring the real inner-join query.
        async fn get_posts_by_tag(&self, tag_id: i32) -> Result<Vec<Post>, RepoError> {
            let store = self.store.lock().unwrap();
            let post_ids: Vec<i32> = store
                .post_tags
                .iter()
                .filter(|(_, tid)| *tid == tag_id)
                .map(|(pid, _)| *pid)
                .collect();
            Ok(store
                .posts
                .iter()
                .filter(|p| p.id.is_some_and(|pid| post_ids.contains(&pid)))
                .cloned()
                .collect())
        }

        async fn get_tags_for_post(&self, post_id: i32) -> Result<Vec<Tag>, RepoError> {
            let store = self.store.lock().unwrap();
            let tag_ids: Vec<i32> = store
                .post_tags
                .iter()
                .filter(|(pid, _)| *pid == post_id)
                .map(|(_, tid)| *tid)
                .collect();
            Ok(store
                .tags
                .iter()
                .filter(|t| t.id.is_some_and(|tid| tag_ids.contains(&tid)))
                .cloned()
                .collect())
        }

        async fn latest_update(&self) -> Result<Option<DateTime<Utc>>, RepoError> {
            let store = self.store.lock().unwrap();
            Ok(store
                .posts
                .iter()
                .filter_map(|p| p.update_date.or(p.createdon).or(p.publishedon))
                .max())
        }
    }

    // -----------------------------------------------------------------------
    // Tags
    // -----------------------------------------------------------------------

    pub struct FakeTagRepo {
        store: SharedStore,
    }

    impl FakeTagRepo {
        pub fn new(store: SharedStore) -> Self {
            Self { store }
        }
    }

    #[async_trait]
    impl Repository<Tag, i32> for FakeTagRepo {
        async fn get_by_id(&self, id: i32) -> Result<Option<Tag>, RepoError> {
            let store = self.store.lock().unwrap();
            Ok(store.tags.iter().find(|t| t.id == Some(id)).cloned())
        }

        async fn get_all(&self) -> Result<Vec<Tag>, RepoError> {
            let store = self.store.lock().unwrap();
            Ok(store.tags.clone())
        }

        async fn create(&self, entity: &Tag) -> Result<Tag, RepoError> {
            let mut store = self.store.lock().unwrap();
            if store.tags.iter().any(|t| t.alias == entity.alias) {
                return Err(RepoError::Conflict(format!(
                    "duplicate key value violates unique constraint on tags.alias: {}",
                    entity.alias
                )));
            }
            let id = next_id(&mut store);
            let mut tag = entity.clone();
            tag.id = Some(id);
            store.tags.push(tag.clone());
            Ok(tag)
        }

        async fn update(&self, entity: &Tag) -> Result<Tag, RepoError> {
            let mut store = self.store.lock().unwrap();
            let Some(idx) = store.tags.iter().position(|t| t.id == entity.id) else {
                return Err(RepoError::NotFound);
            };
            store.tags[idx] = entity.clone();
            Ok(entity.clone())
        }

        async fn delete(&self, id: i32) -> Result<bool, RepoError> {
            let mut store = self.store.lock().unwrap();
            let before = store.tags.len();
            store.tags.retain(|t| t.id != Some(id));
            Ok(store.tags.len() != before)
        }
    }

    #[async_trait]
    impl TagRepository for FakeTagRepo {
        async fn get_by_alias(&self, alias: &str) -> Result<Option<Tag>, RepoError> {
            let store = self.store.lock().unwrap();
            Ok(store.tags.iter().find(|t| t.alias == alias).cloned())
        }

        async fn get_tags_for_post(&self, post_id: i32) -> Result<Vec<Tag>, RepoError> {
            let store = self.store.lock().unwrap();
            let tag_ids: Vec<i32> = store
                .post_tags
                .iter()
                .filter(|(pid, _)| *pid == post_id)
                .map(|(_, tid)| *tid)
                .collect();
            Ok(store
                .tags
                .iter()
                .filter(|t| t.id.is_some_and(|tid| tag_ids.contains(&tid)))
                .cloned()
                .collect())
        }
    }

    // -----------------------------------------------------------------------
    // Users
    // -----------------------------------------------------------------------

    pub struct FakeUserRepo {
        store: SharedStore,
    }

    impl FakeUserRepo {
        pub fn new(store: SharedStore) -> Self {
            Self { store }
        }
    }

    #[async_trait]
    impl Repository<User, i32> for FakeUserRepo {
        async fn get_by_id(&self, id: i32) -> Result<Option<User>, RepoError> {
            let store = self.store.lock().unwrap();
            Ok(store.users.iter().find(|u| u.id == Some(id)).cloned())
        }

        async fn get_all(&self) -> Result<Vec<User>, RepoError> {
            let store = self.store.lock().unwrap();
            Ok(store.users.clone())
        }

        /// No unique constraint on `users.name` in the schema, so unlike the
        /// alias-bearing models there is no conflict check here.
        async fn create(&self, entity: &User) -> Result<User, RepoError> {
            let mut store = self.store.lock().unwrap();
            let id = next_id(&mut store);
            let mut user = entity.clone();
            user.id = Some(id);
            store.users.push(user.clone());
            Ok(user)
        }

        async fn update(&self, entity: &User) -> Result<User, RepoError> {
            let mut store = self.store.lock().unwrap();
            let Some(idx) = store.users.iter().position(|u| u.id == entity.id) else {
                return Err(RepoError::NotFound);
            };
            store.users[idx] = entity.clone();
            Ok(entity.clone())
        }

        async fn delete(&self, id: i32) -> Result<bool, RepoError> {
            let mut store = self.store.lock().unwrap();
            let before = store.users.len();
            store.users.retain(|u| u.id != Some(id));
            Ok(store.users.len() != before)
        }
    }

    #[async_trait]
    impl UserRepository for FakeUserRepo {
        async fn get_by_name(&self, name: &str) -> Result<Option<User>, RepoError> {
            let store = self.store.lock().unwrap();
            Ok(store.users.iter().find(|u| u.name == name).cloned())
        }

        /// Load by name and verify with `domain::security::verify_password`;
        /// unknown name or hash mismatch → `Ok(None)` (mirrors the real repo).
        async fn authenticate(
            &self,
            name: &str,
            password: &str,
        ) -> Result<Option<User>, RepoError> {
            let store = self.store.lock().unwrap();
            let Some(user) = store.users.iter().find(|u| u.name == name) else {
                return Ok(None);
            };
            if domain::security::verify_password(password, &user.password) {
                Ok(Some(user.clone()))
            } else {
                Ok(None)
            }
        }
    }

    // -----------------------------------------------------------------------
    // Categories
    // -----------------------------------------------------------------------

    pub struct FakeCategoryRepo {
        store: SharedStore,
    }

    impl FakeCategoryRepo {
        pub fn new(store: SharedStore) -> Self {
            Self { store }
        }
    }

    #[async_trait]
    impl Repository<Category, i32> for FakeCategoryRepo {
        async fn get_by_id(&self, id: i32) -> Result<Option<Category>, RepoError> {
            let store = self.store.lock().unwrap();
            Ok(store.categories.iter().find(|c| c.id == Some(id)).cloned())
        }

        async fn get_all(&self) -> Result<Vec<Category>, RepoError> {
            let store = self.store.lock().unwrap();
            Ok(store.categories.clone())
        }

        async fn create(&self, entity: &Category) -> Result<Category, RepoError> {
            let mut store = self.store.lock().unwrap();
            if store.categories.iter().any(|c| c.alias == entity.alias) {
                return Err(RepoError::Conflict(format!(
                    "duplicate key value violates unique constraint on categories.alias: {}",
                    entity.alias
                )));
            }
            let id = next_id(&mut store);
            let mut category = entity.clone();
            category.id = Some(id);
            store.categories.push(category.clone());
            Ok(category)
        }

        async fn update(&self, entity: &Category) -> Result<Category, RepoError> {
            let mut store = self.store.lock().unwrap();
            let Some(idx) = store.categories.iter().position(|c| c.id == entity.id) else {
                return Err(RepoError::NotFound);
            };
            store.categories[idx] = entity.clone();
            Ok(entity.clone())
        }

        async fn delete(&self, id: i32) -> Result<bool, RepoError> {
            let mut store = self.store.lock().unwrap();
            let before = store.categories.len();
            store.categories.retain(|c| c.id != Some(id));
            Ok(store.categories.len() != before)
        }
    }

    #[async_trait]
    impl CategoryRepository for FakeCategoryRepo {
        async fn get_by_alias(&self, alias: &str) -> Result<Option<Category>, RepoError> {
            let store = self.store.lock().unwrap();
            Ok(store.categories.iter().find(|c| c.alias == alias).cloned())
        }
    }

    // -----------------------------------------------------------------------
    // Icons
    // -----------------------------------------------------------------------

    pub struct FakeIconRepo {
        store: SharedStore,
    }

    impl FakeIconRepo {
        pub fn new(store: SharedStore) -> Self {
            Self { store }
        }
    }

    #[async_trait]
    impl Repository<Icon, i32> for FakeIconRepo {
        async fn get_by_id(&self, id: i32) -> Result<Option<Icon>, RepoError> {
            let store = self.store.lock().unwrap();
            Ok(store.icons.iter().find(|i| i.id == Some(id)).cloned())
        }

        async fn get_all(&self) -> Result<Vec<Icon>, RepoError> {
            let store = self.store.lock().unwrap();
            Ok(store.icons.clone())
        }

        /// Both `title` and `url` are unique in the schema.
        async fn create(&self, entity: &Icon) -> Result<Icon, RepoError> {
            let mut store = self.store.lock().unwrap();
            if store
                .icons
                .iter()
                .any(|i| i.title == entity.title || i.url == entity.url)
            {
                return Err(RepoError::Conflict(format!(
                    "duplicate key value violates unique constraint on icons.title/url: {}",
                    entity.title
                )));
            }
            let id = next_id(&mut store);
            let mut icon = entity.clone();
            icon.id = Some(id);
            store.icons.push(icon.clone());
            Ok(icon)
        }

        async fn update(&self, entity: &Icon) -> Result<Icon, RepoError> {
            let mut store = self.store.lock().unwrap();
            let Some(idx) = store.icons.iter().position(|i| i.id == entity.id) else {
                return Err(RepoError::NotFound);
            };
            store.icons[idx] = entity.clone();
            Ok(entity.clone())
        }

        async fn delete(&self, id: i32) -> Result<bool, RepoError> {
            let mut store = self.store.lock().unwrap();
            let before = store.icons.len();
            store.icons.retain(|i| i.id != Some(id));
            Ok(store.icons.len() != before)
        }
    }

    #[async_trait]
    impl IconRepository for FakeIconRepo {
        async fn get_by_title(&self, title: &str) -> Result<Option<Icon>, RepoError> {
            let store = self.store.lock().unwrap();
            Ok(store.icons.iter().find(|i| i.title == title).cloned())
        }
    }
}
