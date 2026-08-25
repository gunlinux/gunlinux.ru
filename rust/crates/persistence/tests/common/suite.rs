//! The repository CRUD/finder suite — backend-agnostic test bodies.
//!
//! Port of `tests/test_repositories.py`. Each `pub async fn` takes a migrated
//! `&DatabaseConnection`; `tests/repositories.rs` wires each body to a fresh
//! scratch PostgreSQL database (per-test `provision` + `cleanup`).

use chrono::{DateTime, Utc};
use domain::repositories::{
    CategoryRepository as _, IconRepository as _, PostRepository as _, Repository,
    TagRepository as _, UserRepository as _,
};
use domain::{Category, Icon, Post, Tag, User, Visit, VisitRepository as _};
use persistence::repositories::{
    CategoryRepository, IconRepository, PostRepository, TagRepository, UserRepository,
    VisitRepository,
};
use sea_orm::DatabaseConnection;

pub async fn post_crud(db: &DatabaseConnection) {
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

pub async fn post_update_not_found_is_notfound(db: &DatabaseConnection) {
    let repo = PostRepository::new(db.clone());

    let mut post = Post::new("X", "x", "y");
    post.id = Some(9999);
    let err = repo.update(&post).await.unwrap_err();
    assert!(matches!(err, domain::RepoError::NotFound));
}

pub async fn post_duplicate_alias_is_conflict(db: &DatabaseConnection) {
    let repo = PostRepository::new(db.clone());

    let post = Post::new("First", "dup-alias", "a");
    repo.create(&post).await.unwrap();

    let duplicate = Post::new("Second", "dup-alias", "b");
    let err = repo.create(&duplicate).await.unwrap_err();
    assert!(matches!(err, domain::RepoError::Conflict(_)));
}

pub async fn post_published(db: &DatabaseConnection) {
    let repo = PostRepository::new(db.clone());

    let mut post = Post::new("Published", "published-repo", "x");
    let published_on = Utc::now();
    post.publishedon = Some(published_on);
    repo.create(&post).await.unwrap();

    let published = repo.get_published_posts().await.unwrap();
    assert!(published.iter().any(|p| p.alias == "published-repo"));

    // The timezone-aware datetime must round-trip through the backend.
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

pub async fn post_tag_relations_and_page_queries(db: &DatabaseConnection) {
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
    .insert(db)
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

pub async fn tag_crud(db: &DatabaseConnection) {
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

pub async fn user_crud(db: &DatabaseConnection) {
    let repo = UserRepository::new(db.clone());

    let hashed = domain::security::hash_password("pass123").unwrap();
    let user = User::new("repouser", &hashed);
    let created = repo.create(&user).await.unwrap();
    assert!(created.id.is_some());

    let fetched = repo.get_by_name("repouser").await.unwrap();
    assert!(fetched.is_some());
    assert_eq!(fetched.unwrap().name, "repouser");
}

pub async fn user_authenticate(db: &DatabaseConnection) {
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

pub async fn category_crud(db: &DatabaseConnection) {
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

pub async fn icon_crud(db: &DatabaseConnection) {
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

pub async fn visit_repo(db: &DatabaseConnection) {
    let repo = VisitRepository::new(db.clone());

    let now = Utc::now();
    let old = now - chrono::Duration::days(40);
    let visit = |at: DateTime<Utc>, path: &str, referrer: Option<&str>, ip: Option<&str>| Visit {
        id: None,
        visited_at: at,
        referrer: referrer.map(String::from),
        path: path.to_string(),
        ip_hash: ip.map(String::from),
    };

    repo.record(&visit(now, "/", Some("habr.com"), Some("h1")))
        .await
        .unwrap();
    repo.record(&visit(now, "/rust", Some("habr.com"), Some("h2")))
        .await
        .unwrap();
    repo.record(&visit(now, "/rust", None, Some("h1")))
        .await
        .unwrap();
    // Outside the 30-day window used below — must be excluded everywhere.
    repo.record(&visit(old, "/", Some("google.com"), Some("h9")))
        .await
        .unwrap();

    // Totals: all time vs the last 30 days.
    assert_eq!(repo.total_views(None).await.unwrap(), 4);
    let since_30d = Some(now - chrono::Duration::days(30));
    assert_eq!(repo.total_views(since_30d).await.unwrap(), 3);
    assert_eq!(repo.unique_visitors(since_30d).await.unwrap(), 2);

    // Sources: habr.com (2) first, then direct (1); google.com fell out of
    // the window.
    let sources = repo.referrer_counts(since_30d, 10).await.unwrap();
    assert_eq!(sources.len(), 2);
    assert_eq!(sources[0].referrer.as_deref(), Some("habr.com"));
    assert_eq!(sources[0].count, 2);
    assert_eq!(sources[1].referrer, None);
    assert_eq!(sources[1].count, 1);

    // Landing pages: /rust (2) beats / (1).
    let paths = repo.top_paths(since_30d, 10).await.unwrap();
    assert_eq!(paths.len(), 2);
    assert_eq!(paths[0].path, "/rust");
    assert_eq!(paths[0].count, 2);
    assert_eq!(paths[1].path, "/");
    assert_eq!(paths[1].count, 1);

    // Daily counts: only today has rows within the 14-day window.
    let daily = repo.daily_counts(14).await.unwrap();
    assert_eq!(daily.len(), 1);
    assert_eq!(daily[0].day, now.date_naive());
    assert_eq!(daily[0].count, 3);

    // The limit truncates the result set.
    let sources = repo.referrer_counts(since_30d, 1).await.unwrap();
    assert_eq!(sources.len(), 1);
}
