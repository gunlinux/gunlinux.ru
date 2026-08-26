//! Use-case tests for the `application` crate — the layer the web handlers
//! are thin translators over. Exercises the interactors with in-memory fake
//! repositories (no HTTP, no real DB), pinning the rules that used to live
//! inside axum handlers:
//!
//! - read path: the published-or-page 404 rule, nav pages, year grouping,
//!   tag-view resolution;
//! - admin writes: form → entity translation (publishedon parsing, tag CSV,
//!   is_page), the `posts_tags` FK clear-before-delete, the user
//!   password hash / blank-keeps-hash rule.

use std::collections::HashMap;

use application::{admin, posts};
use chrono::{Datelike, Utc};
use domain::{Post, PostRepository, Repository, Tag, User};
use fakes::{FakePostRepo, FakeTagRepo, FakeUserRepo, SharedStore};

fn form(pairs: &[(&str, &str)]) -> HashMap<String, String> {
    pairs
        .iter()
        .map(|(k, v)| (k.to_string(), v.to_string()))
        .collect()
}

fn published_post(alias: &str, year: i32) -> Post {
    let now = Utc::now();
    Post {
        publishedon: Some(now.with_year(year).unwrap()),
        ..Post::new(alias, alias, "content")
    }
}

// ---------------------------------------------------------------------------
// Read path
// ---------------------------------------------------------------------------

#[tokio::test]
async fn posts_by_year_groups_published_content_desc() {
    let repo = FakePostRepo::new(SharedStore::default());
    repo.create(&published_post("p2026", 2026)).await.unwrap();
    repo.create(&published_post("p2024", 2024)).await.unwrap();
    // Drafts and pages are not blog content.
    repo.create(&Post::new("draft", "draft", "x"))
        .await
        .unwrap();
    let mut page = published_post("page", 2026);
    page.is_page = true;
    repo.create(&page).await.unwrap();

    let groups = posts::posts_by_year(&repo).await.unwrap();
    let years: Vec<i32> = groups.iter().map(|g| g.year).collect();
    assert_eq!(years, vec![2026, 2024]);
    let aliases: Vec<&str> = groups[0].posts.iter().map(|p| p.alias.as_str()).collect();
    assert_eq!(aliases, vec!["p2026"]);
}

#[tokio::test]
async fn resolve_post_view_returns_published_post_with_tags() {
    let store = SharedStore::default();
    let repo = FakePostRepo::new(store.clone());
    let tags = FakeTagRepo::new(store.clone());
    let post = repo.create(&published_post("hello", 2026)).await.unwrap();
    let tag = tags
        .create(&Tag {
            id: None,
            title: "Rust".to_string(),
            alias: "rust".to_string(),
        })
        .await
        .unwrap();
    store
        .lock()
        .unwrap()
        .post_tags
        .push((post.id.unwrap(), tag.id.unwrap()));

    let (found, found_tags) = posts::resolve_post_view(&repo, "hello")
        .await
        .unwrap()
        .expect("published post resolves");
    assert_eq!(found.alias, "hello");
    assert_eq!(found_tags.len(), 1);
    assert_eq!(found_tags[0].alias, "rust");
}

#[tokio::test]
async fn resolve_post_view_draft_is_none() {
    let repo = FakePostRepo::new(SharedStore::default());
    repo.create(&Post::new("draft", "draft", "secret"))
        .await
        .unwrap();
    assert!(posts::resolve_post_view(&repo, "draft")
        .await
        .unwrap()
        .is_none());
}

#[tokio::test]
async fn resolve_post_view_unpublished_page_resolves() {
    let repo = FakePostRepo::new(SharedStore::default());
    let mut page = Post::new("About", "about", "page content");
    page.is_page = true;
    page.publishedon = None;
    repo.create(&page).await.unwrap();
    assert!(posts::resolve_post_view(&repo, "about")
        .await
        .unwrap()
        .is_some());
}

#[tokio::test]
async fn resolve_post_view_unknown_alias_is_none() {
    let repo = FakePostRepo::new(SharedStore::default());
    assert!(posts::resolve_post_view(&repo, "ghost")
        .await
        .unwrap()
        .is_none());
}

#[tokio::test]
async fn resolve_tag_view_returns_tag_and_posts() {
    let store = SharedStore::default();
    let repo = FakePostRepo::new(store.clone());
    let tags = FakeTagRepo::new(store.clone());
    let tagged = repo.create(&published_post("tagged", 2026)).await.unwrap();
    let other = repo.create(&published_post("other", 2026)).await.unwrap();
    let tag = tags
        .create(&Tag {
            id: None,
            title: "Rust".to_string(),
            alias: "rust".to_string(),
        })
        .await
        .unwrap();
    store
        .lock()
        .unwrap()
        .post_tags
        .push((tagged.id.unwrap(), tag.id.unwrap()));

    let (found, tag_posts) = posts::resolve_tag_view(&tags, &repo, "rust")
        .await
        .unwrap()
        .expect("known tag resolves");
    assert_eq!(found.alias, "rust");
    let aliases: Vec<&str> = tag_posts.iter().map(|p| p.alias.as_str()).collect();
    assert_eq!(aliases, vec!["tagged"]);
    assert!(!aliases.contains(&"other"));
}

#[tokio::test]
async fn resolve_tag_view_unknown_tag_is_none() {
    let store = SharedStore::default();
    let repo = FakePostRepo::new(store.clone());
    let tags = FakeTagRepo::new(store.clone());
    assert!(posts::resolve_tag_view(&tags, &repo, "ghost")
        .await
        .unwrap()
        .is_none());
}

#[tokio::test]
async fn nav_pages_returns_only_pages() {
    let repo = FakePostRepo::new(SharedStore::default());
    let mut page = Post::new("About", "about", "x");
    page.is_page = true;
    repo.create(&page).await.unwrap();
    repo.create(&published_post("blog", 2026)).await.unwrap();

    let pages = posts::nav_pages(&repo).await.unwrap();
    let aliases: Vec<&str> = pages.iter().map(|p| p.alias.as_str()).collect();
    assert_eq!(aliases, vec!["about"]);
}

#[tokio::test]
async fn published_posts_and_pages_feed_reads() {
    let repo = FakePostRepo::new(SharedStore::default());
    let mut page = published_post("page", 2026);
    page.is_page = true;
    page.category_id = Some(1);
    repo.create(&page).await.unwrap();
    repo.create(&published_post("blog", 2026)).await.unwrap();
    repo.create(&Post::new("draft", "draft", "x"))
        .await
        .unwrap();

    let pages = posts::page_posts(&repo).await.unwrap();
    assert_eq!(pages.len(), 1);
    assert_eq!(pages[0].alias, "page");
    // The RSS/sitemap listing excludes pages and drafts.
    let feed = posts::published_posts(&repo).await.unwrap();
    let aliases: Vec<&str> = feed.iter().map(|p| p.alias.as_str()).collect();
    assert_eq!(aliases, vec!["blog"]);
}

// ---------------------------------------------------------------------------
// Admin writes
// ---------------------------------------------------------------------------

#[tokio::test]
async fn create_post_translates_form() {
    let repo = FakePostRepo::new(SharedStore::default());
    let publishedon = Utc::now().to_rfc3339();
    let f = form(&[
        ("pagetitle", "Hello"),
        ("alias", "hello"),
        ("content", "world"),
        ("publishedon", &publishedon),
        ("category_id", "3"),
        ("tags", "1, 2"),
        ("is_page", "on"),
    ]);
    admin::create_post(&repo, &f).await.unwrap();

    let post = repo.get_by_alias("hello").await.unwrap().unwrap();
    assert_eq!(post.pagetitle, "Hello");
    assert!(post.publishedon.is_some());
    assert_eq!(post.category_id, Some(3));
    assert!(post.is_page);
    let id = post.id.unwrap();
    let links = repo.get_tags_for_post(id).await.unwrap();
    // The fake does not validate tag existence; the CSV is parsed to ids.
    assert_eq!(links.len(), 0); // no tags exist in the store, so no resolved tags
    let store = repo.0.lock().unwrap();
    let raw: Vec<i32> = store
        .post_tags
        .iter()
        .filter(|(pid, _)| *pid == id)
        .map(|(_, tid)| *tid)
        .collect();
    assert_eq!(raw, vec![1, 2]);
}

#[tokio::test]
async fn create_post_empty_publishedon_is_draft() {
    let repo = FakePostRepo::new(SharedStore::default());
    let f = form(&[("pagetitle", "Draft"), ("alias", "draft"), ("content", "x")]);
    admin::create_post(&repo, &f).await.unwrap();
    let post = repo.get_by_alias("draft").await.unwrap().unwrap();
    assert!(post.publishedon.is_none());
}

#[tokio::test]
async fn update_post_preserves_identity_and_bumps_version() {
    let repo = FakePostRepo::new(SharedStore::default());
    let original = published_post("hello", 2026);
    let created = repo.create(&original).await.unwrap();
    let original_update = created.update_date;

    let f = form(&[
        ("pagetitle", "Hello 2"),
        ("alias", "hello"),
        ("content", "edited"),
        ("publishedon", ""),
        ("is_page", ""),
    ]);
    admin::update_post(&repo, created.id.unwrap(), &f)
        .await
        .unwrap();

    let updated = repo.get_by_alias("hello").await.unwrap().unwrap();
    assert_eq!(updated.pagetitle, "Hello 2");
    assert_eq!(updated.createdon, created.createdon);
    // The version field must be bumped so cached pages re-render.
    assert!(updated.update_date.is_some());
    assert!(updated.update_date.unwrap() > original_update.unwrap());
    assert_eq!(updated.content, "edited");
}

#[tokio::test]
async fn update_post_missing_id_is_not_found() {
    let repo = FakePostRepo::new(SharedStore::default());
    let err = admin::update_post(&repo, 999, &form(&[]))
        .await
        .unwrap_err();
    assert!(matches!(err, application::AppError::NotFound));
}

#[tokio::test]
async fn delete_post_clears_tag_links_first() {
    let store = SharedStore::default();
    let repo = FakePostRepo::new(store.clone());
    let post = repo.create(&published_post("bye", 2026)).await.unwrap();
    store.lock().unwrap().post_tags.push((post.id.unwrap(), 1));

    assert!(admin::delete_post(&repo, post.id.unwrap()).await.unwrap());
    let store = store.lock().unwrap();
    assert!(store.post_tags.is_empty());
    assert!(store.posts.iter().all(|p| p.id != Some(post.id.unwrap())));
}

#[tokio::test]
async fn update_user_blank_password_keeps_hash() {
    let repo = FakeUserRepo::new(SharedStore::default());
    let hashed = domain::security::hash_password("old-pass").unwrap();
    let user = repo
        .create(&User::new("admin", hashed.clone()))
        .await
        .unwrap();

    let f = form(&[
        ("name", "admin2"),
        ("password", ""),
        ("authenticated", "on"),
    ]);
    admin::update_user(&repo, user.id.unwrap(), &f)
        .await
        .unwrap();

    let updated = repo.get_by_id(user.id.unwrap()).await.unwrap().unwrap();
    assert_eq!(updated.name, "admin2");
    assert_eq!(
        updated.password, hashed,
        "blank password must keep the hash"
    );
    assert!(updated.authenticated);
}

#[tokio::test]
async fn update_user_new_password_rehashes() {
    let repo = FakeUserRepo::new(SharedStore::default());
    let user = repo
        .create(&User::new(
            "admin",
            domain::security::hash_password("old-pass").unwrap(),
        ))
        .await
        .unwrap();

    let f = form(&[
        ("name", "admin"),
        ("password", "new-pass"),
        ("authenticated", ""),
    ]);
    admin::update_user(&repo, user.id.unwrap(), &f)
        .await
        .unwrap();

    let updated = repo.get_by_id(user.id.unwrap()).await.unwrap().unwrap();
    assert_ne!(updated.password, user.password);
    assert!(domain::security::verify_password(
        "new-pass",
        &updated.password
    ));
    assert!(!updated.authenticated);
}

// ---------------------------------------------------------------------------
// In-memory fake repositories
// ---------------------------------------------------------------------------

mod fakes {
    use std::sync::{Arc, Mutex};

    use async_trait::async_trait;
    use chrono::{DateTime, Utc};
    use domain::{
        Post, PostRepository, RepoError, Repository, Tag, TagRepository, User, UserRepository,
    };

    #[derive(Default)]
    pub struct Store {
        pub posts: Vec<Post>,
        pub tags: Vec<Tag>,
        pub post_tags: Vec<(i32, i32)>,
        pub users: Vec<User>,
        pub next_id: i32,
    }

    pub type SharedStore = Arc<Mutex<Store>>;

    fn next_id(store: &mut Store) -> i32 {
        store.next_id += 1;
        store.next_id
    }

    pub struct FakePostRepo(pub SharedStore);

    impl FakePostRepo {
        pub fn new(store: SharedStore) -> Self {
            Self(store)
        }
    }

    #[async_trait]
    impl Repository<Post, i32> for FakePostRepo {
        async fn get_by_id(&self, id: i32) -> Result<Option<Post>, RepoError> {
            let store = self.0.lock().unwrap();
            Ok(store.posts.iter().find(|p| p.id == Some(id)).cloned())
        }

        async fn get_all(&self) -> Result<Vec<Post>, RepoError> {
            let store = self.0.lock().unwrap();
            Ok(store.posts.clone())
        }

        async fn create(&self, entity: &Post) -> Result<Post, RepoError> {
            let mut store = self.0.lock().unwrap();
            let id = next_id(&mut store);
            let mut post = entity.clone();
            post.id = Some(id);
            store.posts.push(post.clone());
            Ok(post)
        }

        async fn update(&self, entity: &Post) -> Result<Post, RepoError> {
            let mut store = self.0.lock().unwrap();
            let Some(idx) = store.posts.iter().position(|p| p.id == entity.id) else {
                return Err(RepoError::NotFound);
            };
            store.posts[idx] = entity.clone();
            Ok(entity.clone())
        }

        async fn delete(&self, id: i32) -> Result<bool, RepoError> {
            let mut store = self.0.lock().unwrap();
            let before = store.posts.len();
            store.posts.retain(|p| p.id != Some(id));
            Ok(store.posts.len() != before)
        }
    }

    #[async_trait]
    impl PostRepository for FakePostRepo {
        async fn get_by_alias(&self, alias: &str) -> Result<Option<Post>, RepoError> {
            let store = self.0.lock().unwrap();
            Ok(store.posts.iter().find(|p| p.alias == alias).cloned())
        }

        async fn get_published_posts(&self) -> Result<Vec<Post>, RepoError> {
            let store = self.0.lock().unwrap();
            Ok(store
                .posts
                .iter()
                .filter(|p| p.publishedon.is_some() && p.category_id.is_none())
                .cloned()
                .collect())
        }

        async fn get_all_published_content(&self) -> Result<Vec<Post>, RepoError> {
            let store = self.0.lock().unwrap();
            Ok(store
                .posts
                .iter()
                .filter(|p| p.publishedon.is_some() && !p.is_page)
                .cloned()
                .collect())
        }

        async fn get_page_posts(&self) -> Result<Vec<Post>, RepoError> {
            let store = self.0.lock().unwrap();
            Ok(store.posts.iter().filter(|p| p.is_page).cloned().collect())
        }

        async fn get_posts_by_tag(&self, tag_id: i32) -> Result<Vec<Post>, RepoError> {
            let store = self.0.lock().unwrap();
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
            let store = self.0.lock().unwrap();
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
            let store = self.0.lock().unwrap();
            Ok(store
                .posts
                .iter()
                .filter_map(|p| p.update_date.or(p.createdon).or(p.publishedon))
                .max())
        }

        async fn set_tags_for_post(&self, post_id: i32, tag_ids: &[i32]) -> Result<(), RepoError> {
            let mut store = self.0.lock().unwrap();
            store.post_tags.retain(|(pid, _)| *pid != post_id);
            for tag_id in tag_ids {
                store.post_tags.push((post_id, *tag_id));
            }
            Ok(())
        }
    }

    pub struct FakeTagRepo(SharedStore);

    impl FakeTagRepo {
        pub fn new(store: SharedStore) -> Self {
            Self(store)
        }
    }

    #[async_trait]
    impl Repository<Tag, i32> for FakeTagRepo {
        async fn get_by_id(&self, id: i32) -> Result<Option<Tag>, RepoError> {
            let store = self.0.lock().unwrap();
            Ok(store.tags.iter().find(|t| t.id == Some(id)).cloned())
        }

        async fn get_all(&self) -> Result<Vec<Tag>, RepoError> {
            let store = self.0.lock().unwrap();
            Ok(store.tags.clone())
        }

        async fn create(&self, entity: &Tag) -> Result<Tag, RepoError> {
            let mut store = self.0.lock().unwrap();
            let id = next_id(&mut store);
            let mut tag = entity.clone();
            tag.id = Some(id);
            store.tags.push(tag.clone());
            Ok(tag)
        }

        async fn update(&self, entity: &Tag) -> Result<Tag, RepoError> {
            let mut store = self.0.lock().unwrap();
            let Some(idx) = store.tags.iter().position(|t| t.id == entity.id) else {
                return Err(RepoError::NotFound);
            };
            store.tags[idx] = entity.clone();
            Ok(entity.clone())
        }

        async fn delete(&self, id: i32) -> Result<bool, RepoError> {
            let mut store = self.0.lock().unwrap();
            let before = store.tags.len();
            store.tags.retain(|t| t.id != Some(id));
            Ok(store.tags.len() != before)
        }
    }

    #[async_trait]
    impl TagRepository for FakeTagRepo {
        async fn get_by_alias(&self, alias: &str) -> Result<Option<Tag>, RepoError> {
            let store = self.0.lock().unwrap();
            Ok(store.tags.iter().find(|t| t.alias == alias).cloned())
        }

        async fn get_tags_for_post(&self, post_id: i32) -> Result<Vec<Tag>, RepoError> {
            let store = self.0.lock().unwrap();
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

    pub struct FakeUserRepo(SharedStore);

    impl FakeUserRepo {
        pub fn new(store: SharedStore) -> Self {
            Self(store)
        }
    }

    #[async_trait]
    impl Repository<User, i32> for FakeUserRepo {
        async fn get_by_id(&self, id: i32) -> Result<Option<User>, RepoError> {
            let store = self.0.lock().unwrap();
            Ok(store.users.iter().find(|u| u.id == Some(id)).cloned())
        }

        async fn get_all(&self) -> Result<Vec<User>, RepoError> {
            let store = self.0.lock().unwrap();
            Ok(store.users.clone())
        }

        async fn create(&self, entity: &User) -> Result<User, RepoError> {
            let mut store = self.0.lock().unwrap();
            let id = next_id(&mut store);
            let mut user = entity.clone();
            user.id = Some(id);
            store.users.push(user.clone());
            Ok(user)
        }

        async fn update(&self, entity: &User) -> Result<User, RepoError> {
            let mut store = self.0.lock().unwrap();
            let Some(idx) = store.users.iter().position(|u| u.id == entity.id) else {
                return Err(RepoError::NotFound);
            };
            store.users[idx] = entity.clone();
            Ok(entity.clone())
        }

        async fn delete(&self, id: i32) -> Result<bool, RepoError> {
            let mut store = self.0.lock().unwrap();
            let before = store.users.len();
            store.users.retain(|u| u.id != Some(id));
            Ok(store.users.len() != before)
        }
    }

    #[async_trait]
    impl UserRepository for FakeUserRepo {
        async fn get_by_name(&self, name: &str) -> Result<Option<User>, RepoError> {
            let store = self.0.lock().unwrap();
            Ok(store.users.iter().find(|u| u.name == name).cloned())
        }

        async fn authenticate(
            &self,
            name: &str,
            password: &str,
        ) -> Result<Option<User>, RepoError> {
            let store = self.0.lock().unwrap();
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
}
