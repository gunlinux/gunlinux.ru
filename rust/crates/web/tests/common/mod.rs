//! Test helpers: in-memory fake repositories implementing the domain traits,
//! and a helper that builds a fresh `web::Router` around them (a fresh app per
//! call, so tests never share cache or repository state).
#![allow(dead_code)] // each test binary compiles this module and uses a subset

use std::sync::{Arc, Mutex};

use async_trait::async_trait;
use axum::Router;
use domain::{
    Category, CategoryRepository, Icon, IconRepository, Post, PostRepository, RepoError,
    Repository, Tag, TagRepository, User, UserRepository,
};
use web::settings;
use web::{build_app_with_static, AppState};

/// All fake state in one lockable store.
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

// ---------------------------------------------------------------------------
// Posts
// ---------------------------------------------------------------------------

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

    async fn get_page_posts(&self) -> Result<Vec<Post>, RepoError> {
        let store = self.store.lock().unwrap();
        Ok(store.posts.iter().filter(|p| p.is_page).cloned().collect())
    }

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
}

// ---------------------------------------------------------------------------
// Tags
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------

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

    async fn authenticate(&self, name: &str, password: &str) -> Result<Option<User>, RepoError> {
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

// ---------------------------------------------------------------------------
// Categories
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Icons
// ---------------------------------------------------------------------------

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

    async fn create(&self, entity: &Icon) -> Result<Icon, RepoError> {
        let mut store = self.store.lock().unwrap();
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

// ---------------------------------------------------------------------------
// App construction
// ---------------------------------------------------------------------------

/// Build a fresh app + shared store. Each call is fully isolated (fresh cache,
/// fresh repositories), matching the Python `client` fixture.
pub fn test_app() -> (SharedStore, Router) {
    let store = SharedStore::default();
    let app = build_test_app(store.clone());
    (store, app)
}

pub fn build_test_app(store: SharedStore) -> Router {
    // Use the same (env-derived) settings the auth helpers read, so JWT and
    // session signing secrets agree.
    let settings = Arc::new(settings::get_settings().clone());
    let state = AppState::new(
        Arc::new(FakePostRepo::new(store.clone())),
        Arc::new(FakeTagRepo::new(store.clone())),
        Arc::new(FakeUserRepo::new(store.clone())),
        Arc::new(FakeCategoryRepo::new(store.clone())),
        Arc::new(FakeIconRepo::new(store.clone())),
        settings,
    );
    // Point /static at the repo's real static dir: the layout loads htmx from
    // /static/vendor/htmx.min.js (the trimmed local build), and build_app's
    // STATIC_DIR default is relative to the cwd, which does not resolve from
    // the test directory.
    build_app_with_static(
        state,
        concat!(env!("CARGO_MANIFEST_DIR"), "/../../../app/static"),
    )
}

// ---------------------------------------------------------------------------
// Request helpers
// ---------------------------------------------------------------------------

use axum::body::Body;
use axum::http::{Request, StatusCode};
use axum::response::Response;
use tower::ServiceExt;

pub async fn get(app: &Router, uri: &str) -> Response {
    app.clone()
        .oneshot(Request::builder().uri(uri).body(Body::empty()).unwrap())
        .await
        .unwrap()
}

pub async fn get_hx(app: &Router, uri: &str) -> Response {
    app.clone()
        .oneshot(
            Request::builder()
                .uri(uri)
                .header("hx-request", "true")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap()
}

pub async fn post_form(app: &Router, uri: &str, body: &str) -> Response {
    app.clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(uri)
                .header("content-type", "application/x-www-form-urlencoded")
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap()
}

pub async fn post_form_with_cookie(app: &Router, uri: &str, body: &str, cookie: &str) -> Response {
    app.clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(uri)
                .header("content-type", "application/x-www-form-urlencoded")
                .header("cookie", cookie)
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap()
}

pub async fn get_with_cookie(app: &Router, uri: &str, cookie: &str) -> Response {
    app.clone()
        .oneshot(
            Request::builder()
                .uri(uri)
                .header("cookie", cookie)
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap()
}

pub async fn body_text(resp: Response) -> String {
    let bytes = axum::body::to_bytes(resp.into_body(), usize::MAX)
        .await
        .unwrap();
    String::from_utf8_lossy(&bytes).to_string()
}

/// Convenience: assert status and return the body.
pub async fn expect_status(resp: Response, expected: StatusCode) -> String {
    assert_eq!(resp.status(), expected, "unexpected status for request");
    body_text(resp).await
}

/// Seed helpers
pub fn seed_published_post(store: &SharedStore, pagetitle: &str, alias: &str, content: &str) {
    let mut store = store.lock().unwrap();
    let id = next_id(&mut store);
    let post = Post {
        id: Some(id),
        pagetitle: pagetitle.to_string(),
        alias: alias.to_string(),
        content: content.to_string(),
        createdon: Some(chrono::Utc::now()),
        publishedon: Some(chrono::Utc::now()),
        category_id: None,
        is_page: false,
        user_id: None,
    };
    store.posts.push(post);
}

pub fn seed_page(store: &SharedStore, pagetitle: &str, alias: &str) {
    let mut store = store.lock().unwrap();
    let id = next_id(&mut store);
    let post = Post {
        id: Some(id),
        pagetitle: pagetitle.to_string(),
        alias: alias.to_string(),
        content: "page content".to_string(),
        createdon: Some(chrono::Utc::now()),
        publishedon: Some(chrono::Utc::now()),
        category_id: Some(1),
        is_page: true,
        user_id: None,
    };
    store.posts.push(post);
}

pub fn seed_tag(store: &SharedStore, title: &str, alias: &str) {
    let mut store = store.lock().unwrap();
    let id = next_id(&mut store);
    store.tags.push(Tag {
        id: Some(id),
        title: title.to_string(),
        alias: alias.to_string(),
    });
}

pub fn seed_user(store: &SharedStore, name: &str, password: &str) {
    let hashed = domain::security::hash_password(password).unwrap();
    let mut store = store.lock().unwrap();
    let id = next_id(&mut store);
    store.users.push(User {
        id: Some(id),
        name: name.to_string(),
        password: hashed,
        authenticated: false,
        createdon: Some(chrono::Utc::now()),
    });
}

/// Log in via the admin flow and return the `session=...` cookie value.
pub async fn login_cookie(app: &Router, username: &str, password: &str) -> String {
    let body = format!("username={username}&password={password}");
    let resp = post_form(app, "/admin/login", &body).await;
    assert_eq!(
        resp.status(),
        StatusCode::SEE_OTHER,
        "login should redirect"
    );
    let set_cookie = resp
        .headers()
        .get("set-cookie")
        .expect("login should set a session cookie")
        .to_str()
        .unwrap()
        .to_string();
    // `session=<value>; Path=/; ...` — keep only the cookie pair.
    set_cookie.split(';').next().unwrap().trim().to_string()
}
