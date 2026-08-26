//! Error-mapping and fake-repo semantic tests.
//!
//! The service layer (thin pass-through structs over the `domain` repository
//! traits) was superseded by the `application` crate's use cases, which are
//! unit-tested in `application/tests/`. What remains valuable here: pinning
//! `RepoError` → `WebError` mapping and the in-memory fake semantics (which
//! mirror the SeaORM-backed repos in `persistence`).

use domain::{Post, RepoError, Repository};
use fakes::{FakePostRepo, SharedStore};
use web::WebError;

// ---------------------------------------------------------------------------
// Error mapping and fake-repo semantics
// ---------------------------------------------------------------------------

/// The only error path from a repo-backed call is `RepoError` propagated
/// through `From<RepoError> for WebError` via `?`. Pin that mapping directly.
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

/// Fake post repo implementing the `domain` traits with the semantics of the
/// real SeaORM-backed repository (see `persistence/src/repositories`):
///
/// - `get_by_alias` returns `Ok(None)` for unknown aliases;
/// - `create` rejects duplicate `posts.alias` with `RepoError::Conflict` —
///   the in-memory analogue of the DB unique constraint surfacing through
///   `translate_err`;
/// - `update` of a missing id returns `RepoError::NotFound`;
/// - `delete` of a missing id returns `Ok(false)`.
mod fakes {
    use std::sync::{Arc, Mutex};

    use async_trait::async_trait;
    use chrono::{DateTime, Utc};
    use domain::{Post, PostRepository, RepoError, Repository, Tag};

    /// All fake state in one lockable store (one store per test).
    #[derive(Default)]
    pub struct Store {
        pub posts: Vec<Post>,
        pub tags: Vec<Tag>,
        /// (post_id, tag_id) associations for the posts_tags m2m.
        pub post_tags: Vec<(i32, i32)>,
        pub next_id: i32,
    }

    pub type SharedStore = Arc<Mutex<Store>>;

    fn next_id(store: &mut Store) -> i32 {
        store.next_id += 1;
        store.next_id
    }

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

        async fn set_tags_for_post(&self, post_id: i32, tag_ids: &[i32]) -> Result<(), RepoError> {
            let mut store = self.store.lock().unwrap();
            store.post_tags.retain(|(pid, _)| *pid != post_id);
            for tag_id in tag_ids {
                store.post_tags.push((post_id, *tag_id));
            }
            Ok(())
        }
    }
}
