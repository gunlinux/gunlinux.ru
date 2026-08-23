//! Port of `tests/test_repositories.py` — repository CRUD/finder tests run
//! against a temp-file SQLite database with the baseline migration applied.

use chrono::Utc;
use domain::repositories::{
    CategoryRepository as _, IconRepository as _, PostRepository as _, Repository,
    TagRepository as _, UserRepository as _,
};
use domain::{Category, Icon, Post, Tag, User};
use persistence::migrator::{Migrator, MigratorTrait};
use persistence::pool;
use persistence::repositories::{
    CategoryRepository, IconRepository, PostRepository, TagRepository, UserRepository,
};
use sea_orm::DatabaseConnection;

/// Connect to a temp-file SQLite DB and apply all migrations.
/// The `NamedTempFile` is kept alive by the caller for the test's lifetime.
async fn test_db() -> (DatabaseConnection, tempfile::NamedTempFile) {
    let file = tempfile::NamedTempFile::new().expect("create temp sqlite file");
    let url = format!("sqlite://{}?mode=rwc", file.path().display());
    let db = pool::connect(&url).await.expect("connect sqlite");
    Migrator::up(&db, None).await.expect("run migrations");
    (db, file)
}

#[tokio::test]
async fn test_post_crud() {
    let (db, _file) = test_db().await;
    let repo = PostRepository::new(db.clone());

    let post = Post::new("Test Post", "test-post-repo", "content");
    let created = repo.create(&post).await.unwrap();
    assert!(created.id.is_some());

    let fetched = repo.get_by_id(created.id.unwrap()).await.unwrap();
    assert!(fetched.is_some());
    assert_eq!(fetched.unwrap().pagetitle, "Test Post");

    let fetched_alias = repo.get_by_alias("test-post-repo").await.unwrap();
    assert!(fetched_alias.is_some());

    let all = repo.get_all().await.unwrap();
    assert!(all.iter().any(|p| p.alias == "test-post-repo"));

    assert!(repo.delete(created.id.unwrap()).await.unwrap());
}

#[tokio::test]
async fn test_post_update_not_found_is_notfound() {
    let (db, _file) = test_db().await;
    let repo = PostRepository::new(db.clone());

    let mut post = Post::new("X", "x", "y");
    post.id = Some(9999);
    let err = repo.update(&post).await.unwrap_err();
    assert!(matches!(err, domain::RepoError::NotFound));
}

#[tokio::test]
async fn test_post_duplicate_alias_is_conflict() {
    let (db, _file) = test_db().await;
    let repo = PostRepository::new(db.clone());

    let post = Post::new("First", "dup-alias", "a");
    repo.create(&post).await.unwrap();

    let duplicate = Post::new("Second", "dup-alias", "b");
    let err = repo.create(&duplicate).await.unwrap_err();
    assert!(matches!(err, domain::RepoError::Conflict(_)));
}

#[tokio::test]
async fn test_post_published() {
    let (db, _file) = test_db().await;
    let repo = PostRepository::new(db.clone());

    let mut post = Post::new("Published", "published-repo", "x");
    let published_on = Utc::now();
    post.publishedon = Some(published_on);
    repo.create(&post).await.unwrap();

    let published = repo.get_published_posts().await.unwrap();
    assert!(published.iter().any(|p| p.alias == "published-repo"));

    // The timezone-aware datetime must round-trip through SQLite.
    let fetched = repo.get_by_alias("published-repo").await.unwrap().unwrap();
    let stored = fetched.publishedon.expect("publishedon preserved");
    let drift = (published_on - stored).num_seconds().abs();
    assert!(drift <= 1, "publishedon drift: {drift}s");

    // An unpublished post must not appear in the published list.
    let draft = Post::new("Draft", "draft-repo", "y");
    repo.create(&draft).await.unwrap();
    let published = repo.get_published_posts().await.unwrap();
    assert!(!published.iter().any(|p| p.alias == "draft-repo"));
}

#[tokio::test]
async fn test_post_tag_relations_and_page_queries() {
    let (db, _file) = test_db().await;
    let post_repo = PostRepository::new(db.clone());
    let tag_repo = TagRepository::new(db.clone());
    let category_repo = CategoryRepository::new(db.clone());

    let category = Category {
        id: None,
        title: "Tech".into(),
        alias: "tech".into(),
        template: None,
        page: Some(false),
    };
    let category = category_repo.create(&category).await.unwrap();

    let page_category = Category {
        id: None,
        title: "About".into(),
        alias: "about".into(),
        template: None,
        page: Some(true),
    };
    let page_category = category_repo.create(&page_category).await.unwrap();

    let tag = Tag {
        id: None,
        title: "Rust".into(),
        alias: "rust".into(),
    };
    let tag = tag_repo.create(&tag).await.unwrap();

    let mut post = Post::new("Tagged", "tagged-post", "hello");
    post.publishedon = Some(Utc::now());
    post.category_id = category.id;
    let post = post_repo.create(&post).await.unwrap();

    let mut page_post = Post::new("Page", "page-post", "about me");
    page_post.publishedon = Some(Utc::now());
    page_post.category_id = page_category.id;
    let page_post = post_repo.create(&page_post).await.unwrap();

    let mut draft = Post::new("Draft", "draft", "x");
    draft.category_id = page_category.id;
    let _draft = post_repo.create(&draft).await.unwrap();

    // Link post <-> tag through the join table.
    use persistence::entities::posts_tag;
    use sea_orm::{ActiveModelTrait, Set};
    posts_tag::ActiveModel {
        post_id: Set(post.id.unwrap()),
        tag_id: Set(tag.id.unwrap()),
    }
    .insert(&db)
    .await
    .expect("link post to tag");

    let by_tag = post_repo.get_posts_by_tag(tag.id.unwrap()).await.unwrap();
    assert_eq!(by_tag.len(), 1);
    assert_eq!(by_tag[0].alias, "tagged-post");
    assert!(!by_tag[0].is_page);

    let tags_for_post = post_repo.get_tags_for_post(post.id.unwrap()).await.unwrap();
    assert_eq!(tags_for_post.len(), 1);
    assert_eq!(tags_for_post[0].alias, "rust");

    // Published content = published posts whose category page IS NOT TRUE
    // (left-joined, so uncategorised published posts are included too).
    let mut uncategorised = Post::new("Plain", "plain", "p");
    uncategorised.publishedon = Some(Utc::now());
    post_repo.create(&uncategorised).await.unwrap();

    let published = post_repo.get_all_published_content().await.unwrap();
    let aliases: Vec<_> = published.iter().map(|p| p.alias.as_str()).collect();
    assert!(aliases.contains(&"tagged-post"));
    assert!(aliases.contains(&"plain"));
    assert!(!aliases.contains(&"page-post"));
    assert!(!aliases.contains(&"draft"));
    assert!(published.iter().all(|p| !p.is_page));

    let pages = post_repo.get_page_posts().await.unwrap();
    assert!(pages.iter().any(|p| p.alias == "page-post"));
    assert!(pages.iter().all(|p| p.is_page));

    // get_by_id/get_by_alias load the category for the is_page flag.
    let via_id = post_repo
        .get_by_id(page_post.id.unwrap())
        .await
        .unwrap()
        .unwrap();
    assert!(via_id.is_page);
    let via_alias = post_repo.get_by_alias("page-post").await.unwrap().unwrap();
    assert!(via_alias.is_page);
    let tagged = post_repo
        .get_by_alias("tagged-post")
        .await
        .unwrap()
        .unwrap();
    assert!(!tagged.is_page);
}

#[tokio::test]
async fn test_tag_crud() {
    let (db, _file) = test_db().await;
    let repo = TagRepository::new(db.clone());

    let tag = Tag {
        id: None,
        title: "Python".into(),
        alias: "python-repo".into(),
    };
    let created = repo.create(&tag).await.unwrap();
    assert!(created.id.is_some());

    assert!(repo.get_by_id(created.id.unwrap()).await.unwrap().is_some());
    assert!(repo.get_by_alias("python-repo").await.unwrap().is_some());
    assert!(repo.delete(created.id.unwrap()).await.unwrap());
}

#[tokio::test]
async fn test_user_crud() {
    let (db, _file) = test_db().await;
    let repo = UserRepository::new(db.clone());

    let hashed = domain::security::hash_password("pass123").unwrap();
    let user = User::new("repouser", &hashed);
    let created = repo.create(&user).await.unwrap();
    assert!(created.id.is_some());

    let fetched = repo.get_by_name("repouser").await.unwrap();
    assert!(fetched.is_some());
    assert_eq!(fetched.unwrap().name, "repouser");
}

#[tokio::test]
async fn test_user_authenticate() {
    let (db, _file) = test_db().await;
    let repo = UserRepository::new(db.clone());

    let hashed = domain::security::hash_password("secret").unwrap();
    let user = User::new("authrepo", &hashed);
    repo.create(&user).await.unwrap();

    assert!(repo
        .authenticate("authrepo", "secret")
        .await
        .unwrap()
        .is_some());
    assert!(repo
        .authenticate("authrepo", "wrong")
        .await
        .unwrap()
        .is_none());
    // Unknown user name -> None.
    assert!(repo
        .authenticate("no-such-user", "secret")
        .await
        .unwrap()
        .is_none());
}

#[tokio::test]
async fn test_category_crud() {
    let (db, _file) = test_db().await;
    let repo = CategoryRepository::new(db.clone());

    let cat = Category {
        id: None,
        title: "Tech".into(),
        alias: "tech-repo".into(),
        template: None,
        page: Some(false),
    };
    let created = repo.create(&cat).await.unwrap();
    assert!(created.id.is_some());
    assert!(repo.get_by_alias("tech-repo").await.unwrap().is_some());
}

#[tokio::test]
async fn test_icon_crud() {
    let (db, _file) = test_db().await;
    let repo = IconRepository::new(db.clone());

    let icon = Icon {
        id: None,
        title: "GitHub-repo".into(),
        url: "https://github.com/repo".into(),
        content: Some("<svg/>".into()),
    };
    let created = repo.create(&icon).await.unwrap();
    assert!(created.id.is_some());
    assert!(repo.get_by_title("GitHub-repo").await.unwrap().is_some());
    assert!(!repo.get_all().await.unwrap().is_empty());
}
