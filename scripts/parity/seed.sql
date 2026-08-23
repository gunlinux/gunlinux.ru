-- ============================================================================
-- Parity seed data for gunlinux.ru — applied byte-identically to BOTH scratch
-- databases (scripts/parity/tmp/python.db and .../rust.db) via `sqlite3`.
--
-- Rules for this file:
--  * Fixed explicit IDs so both sides see literally identical rows.
--  * Timestamps are RFC3339 ("2026-01-15T12:00:00+00:00") — parseable by both
--    SQLAlchemy (datetime.fromisoformat) and sqlx (rfc3339 decoder), and they
--    round-trip into the same rendered dates on both sides.
--  * No single quotes in text content (avoids SQL escaping mistakes); `&`,
--    `<`, `>` are deliberately included so HTML-escaping drift is visible.
-- ============================================================================

DELETE FROM posts_tags;
DELETE FROM posts;
DELETE FROM categories;
DELETE FROM tags;
DELETE FROM users;
DELETE FROM icons;

-- ---------------------------------------------------------------------------
-- categories
--   1 = regular category (page=0), 2 = "page" category (page=1 -> is_page)
-- ---------------------------------------------------------------------------
INSERT INTO categories (id, title, alias, template, page) VALUES
  (1, 'Технологии', 'tech', NULL, 0),
  (2, 'О сайте', 'about', NULL, 1);

-- ---------------------------------------------------------------------------
-- tags
-- ---------------------------------------------------------------------------
INSERT INTO tags (id, title, alias) VALUES
  (1, 'Rust', 'rust'),
  (2, 'Python', 'python');

-- ---------------------------------------------------------------------------
-- users — admin, password "parity-admin-pass" (bcrypt cost 12)
-- ---------------------------------------------------------------------------
INSERT INTO users (id, name, password, authenticated, createdon) VALUES
  (1, 'admin', '$2b$12$P3yhFpBKtnQOJ4Dd83NffOTnaFwwWJZ4HpE9N02pAe6AWpL1Ls4a2', 1, '2026-01-01T09:00:00+00:00');

-- ---------------------------------------------------------------------------
-- posts
--   1  hello-world  published, category=tech, tags rust+python
--                    content exercises fenced code / raw HTML / inline code /
--                    links with & / emphasis / list / blockquote
--   2  draft-post   unpublished (draft) -> /draft-post must 404
--   3  about-page   published, category=about (page=1) -> is_page post
--   4  long-post    published, NO category -> RSS + sitemap; first paragraph
--                    > 300 chars to exercise teaser truncation
--   5  rss-post     published, NO category -> second RSS/sitemap item
-- ---------------------------------------------------------------------------
INSERT INTO posts (id, pagetitle, alias, content, createdon, publishedon, category_id, user_id) VALUES
  (1,
   'Привет, мир',
   'hello-world',
   'Добро пожаловать в мой **первый** пост про Rust & Axum.

Обычный текст со `inline code` и [ссылкой](https://example.com/?a=1&b=2).

```rust
fn main() {
    println!("hello & goodbye <world>");
}
```

- пункт один
- пункт два

<div class="custom-block">raw html block inside</div>

> цитата для проверки

Текст с <b>inline html</b> внутри.',
   '2026-01-10T10:00:00+00:00', '2026-01-15T12:00:00+00:00', 1, 1);

INSERT INTO posts (id, pagetitle, alias, content, createdon, publishedon, category_id, user_id) VALUES
  (2, 'Черновик', 'draft-post', 'Это черновик — не публиковать.', '2026-01-20T10:00:00+00:00', NULL, NULL, 1);

INSERT INTO posts (id, pagetitle, alias, content, createdon, publishedon, category_id, user_id) VALUES
  (3, 'О сайте & FAQ', 'about-page', 'Сайт про Linux, Rust и Python. Tags: & < > символы тоже.', '2026-02-01T08:00:00+00:00', '2026-02-01T08:00:00+00:00', 2, 1);

INSERT INTO posts (id, pagetitle, alias, content, createdon, publishedon, category_id, user_id) VALUES
  (4,
   'Длинная заметка',
   'long-post',
   'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.

Второй абзац, который не должен попасть в teaser.',
   '2026-03-10T09:30:00+00:00', '2026-03-10T09:30:00+00:00', NULL, 1);

INSERT INTO posts (id, pagetitle, alias, content, createdon, publishedon, category_id, user_id) VALUES
  (5, 'RSS Only Post', 'rss-post', 'Короткая запись только для ленты.', '2026-04-01T12:00:00+00:00', '2026-04-01T12:00:00+00:00', NULL, 1);

-- ---------------------------------------------------------------------------
-- posts_tags — post 1 <-> rust+python, post 4 <-> python
-- ---------------------------------------------------------------------------
INSERT INTO posts_tags (post_id, tag_id) VALUES
  (1, 1),
  (1, 2),
  (4, 2);

-- ---------------------------------------------------------------------------
-- icons
-- ---------------------------------------------------------------------------
INSERT INTO icons (id, title, url, content) VALUES
  (1, 'GitHub', 'https://github.com/example', '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg>'),
  (2, 'Telegram', 'https://t.me/example', '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>');
