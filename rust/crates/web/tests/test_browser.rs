//! Real-browser (headless Chromium) end-to-end tests for htmx swaps.
//!
//! The rest of the suite verifies htmx only at the HTTP level (fragments
//! return 200). These tests go further: they run the axum app on a real
//! loopback port, drive it with a real headless browser, and prove that
//! JavaScript actually executes — htmx issues the request and the returned
//! fragment replaces the swap target in the DOM.
//!
//! # How to run
//!
//! ```text
//! cargo test -p web --features browser-tests --test test_browser
//! ```
//!
//! The whole file is gated behind the `browser-tests` feature (see
//! `Cargo.toml`), so the default `cargo test` neither compiles nor runs it.
//!
//! # Browser binary
//!
//! A Chrome/Chromium binary is resolved in this order:
//! 1. `CHROME` env var — must point at an existing binary;
//! 2. chromiumoxide's auto-detection (well-known install paths and `PATH`,
//!    e.g. macOS `/Applications/Google Chrome.app/Contents/MacOS/Google
//!    Chrome`, Linux `/usr/bin/google-chrome`, `/usr/bin/chromium`);
//! 3. a pinned Chromium build downloaded via `chromiumoxide_fetcher` into
//!    `$HOME/.cache/chromiumoxide` (reused on later runs; needs network).
//!
//! GitHub Actions `ubuntu-latest` runners already ship Google Chrome, so no
//! browser-install step is required there. On other Linux runners install one
//! (`sudo apt-get install -y chromium-browser`) or set `CHROME=/path/to/chrome`.
//!
//! # Network
//!
//! The templates load htmx from the jsdelivr CDN (as in production), so the
//! browser needs outbound HTTPS to `cdn.jsdelivr.net`. If htmx never loads,
//! the tests fail with a message pointing here.
//!
//! # What is asserted
//!
//! An init script registers a `htmx:afterSwap` listener before any page code
//! runs, counting swaps whose target is `.page__content`. Each test waits for
//! that counter (or a DOM condition) instead of sleeping, so htmx's async
//! requests are always settled before assertions. Dual-mode consistency is
//! checked by comparing the swapped-in DOM against the fragment the same
//! endpoint returns for an `HX-Request` at the HTTP level.

#![cfg(feature = "browser-tests")]

mod common;

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::{Duration, Instant};

use chromiumoxide::page::Page;
use chromiumoxide::{Browser, BrowserConfig};
use chromiumoxide_fetcher::{BrowserFetcher, BrowserFetcherOptions};
use domain::Icon;
use futures::StreamExt;
use tokio::task::JoinHandle;

use common::{body_text, get_hx, seed_page, seed_published_post, test_app};

/// How long to wait for a single DOM/swap condition (htmx is async).
const SWAP_TIMEOUT: Duration = Duration::from_secs(20);
/// Budget for launching the browser binary.
const LAUNCH_TIMEOUT: Duration = Duration::from_secs(60);

/// Unique-per-launch browser profile directory (see `TestBrowser::launch`).
static BROWSER_SEQ: AtomicUsize = AtomicUsize::new(0);

// ---------------------------------------------------------------------------
// Test app server
// ---------------------------------------------------------------------------

/// Serve the router on an ephemeral loopback port and return its base URL
/// plus the server task handle (caller aborts it for teardown).
async fn serve(app: axum::Router) -> (String, JoinHandle<()>) {
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind an ephemeral loopback port");
    let url = format!("http://{}", listener.local_addr().expect("local addr"));
    let handle = tokio::spawn(async move {
        let _ = axum::serve(listener, app).await;
    });
    (url, handle)
}

/// Wait until the test server accepts TCP connections (the serve task is
/// spawned before we navigate, so there is a tiny race otherwise).
async fn wait_for_server(url: &str) {
    let addr = url.strip_prefix("http://").expect("http url");
    let deadline = Instant::now() + Duration::from_secs(10);
    loop {
        if tokio::net::TcpStream::connect(addr).await.is_ok() {
            return;
        }
        assert!(
            Instant::now() < deadline,
            "test server at {url} never accepted connections"
        );
        tokio::time::sleep(Duration::from_millis(50)).await;
    }
}

// ---------------------------------------------------------------------------
// Headless browser
// ---------------------------------------------------------------------------

/// A launched headless browser plus its CDP event-handler task.
///
/// `Drop` kills the browser child process, so teardown happens even when a
/// test panics mid-way.
struct TestBrowser {
    browser: Option<Browser>,
    handler: Option<JoinHandle<()>>,
    user_data_dir: PathBuf,
}

impl TestBrowser {
    async fn launch() -> Self {
        // A unique profile dir per launch, computed BEFORE the config is
        // built: chromiumoxide would otherwise reuse a single temp dir, and
        // parallel tests would fight over Chrome's profile lock.
        let user_data_dir = std::env::temp_dir().join(format!(
            "gunlinux-browser-test-{}-{}",
            std::process::id(),
            BROWSER_SEQ.fetch_add(1, Ordering::Relaxed),
        ));
        // Remove any stale profile from a previously crashed run.
        let _ = std::fs::remove_dir_all(&user_data_dir);

        let config = browser_config(&user_data_dir).await;
        let (browser, mut handler) = Browser::launch(config)
            .await
            .expect("launch headless browser");
        let handler = tokio::spawn(async move { while handler.next().await.is_some() {} });
        Self {
            browser: Some(browser),
            handler: Some(handler),
            user_data_dir,
        }
    }

    async fn new_page(&self) -> Page {
        self.browser
            .as_ref()
            .expect("browser already closed")
            .new_page("about:blank")
            .await
            .expect("create a new page")
    }

    /// Graceful shutdown; `Drop` covers the panic path.
    async fn close(&mut self) {
        if let Some(mut browser) = self.browser.take() {
            let _ = browser.close().await;
        }
        if let Some(handler) = self.handler.take() {
            let _ = handler.await;
        }
        let _ = std::fs::remove_dir_all(&self.user_data_dir);
    }
}

impl Drop for TestBrowser {
    fn drop(&mut self) {
        // Dropping `Browser` kills the spawned child process.
        self.browser.take();
        if let Some(handler) = self.handler.take() {
            handler.abort();
        }
    }
}

/// Resolve a Chrome/Chromium binary and build the browser config.
///
/// Resolution order (see the module docs): `CHROME` env var, then
/// chromiumoxide's auto-detection, then a pinned download via
/// `chromiumoxide_fetcher` cached in `$HOME/.cache/chromiumoxide`.
async fn browser_config(user_data_dir: &Path) -> BrowserConfig {
    let mut builder = BrowserConfig::builder()
        .no_sandbox()
        .new_headless_mode()
        .user_data_dir(user_data_dir)
        .arg("--disable-gpu")
        .arg("--disable-dev-shm-usage")
        .arg("--disable-crash-reporter")
        .launch_timeout(LAUNCH_TIMEOUT)
        .request_timeout(Duration::from_secs(30));

    if let Ok(path) = std::env::var("CHROME") {
        if !Path::new(&path).is_file() {
            panic!("CHROME is set to {path:?} but no such file exists");
        }
        builder = builder.chrome_executable(&path);
        return builder.build().expect("browser config (CHROME)");
    }

    // `build()` runs the executable auto-detection and only fails when no
    // browser is found — that is the signal to download one.
    match builder.clone().build() {
        Ok(config) => config,
        Err(not_found) => {
            eprintln!(
                "no local Chrome/Chromium found ({not_found}); \
                 downloading a pinned build via chromiumoxide_fetcher"
            );
            let options =
                BrowserFetcherOptions::default().expect("fetcher options (unsupported platform)");
            let installation = BrowserFetcher::new(options)
                .fetch()
                .await
                .expect("download Chromium (network required)");
            eprintln!(
                "downloaded Chromium to {}",
                installation.executable_path.display()
            );
            builder
                .chrome_executable(installation.executable_path)
                .build()
                .expect("browser config (fetched binary)")
        }
    }
}

// ---------------------------------------------------------------------------
// DOM helpers
// ---------------------------------------------------------------------------

/// Inject a swap counter before ANY page code runs, so load-triggered htmx
/// requests (`hx-trigger="load"`) are observed too. `htmx:afterSwap` fires
/// with `event.detail.target` set to the swap target element.
const INSTRUMENT: &str = r#"
    window.__htmxSwaps = 0;
    window.__pageContentSwaps = 0;
    document.addEventListener('htmx:afterSwap', function (e) {
        window.__htmxSwaps += 1;
        var t = e.detail && e.detail.target;
        if (t && t.classList && t.classList.contains('page__content')) {
            window.__pageContentSwaps += 1;
        }
    });
"#;

/// Poll `js_condition` (a JS expression evaluating to a boolean) until it is
/// true or `timeout` elapses.
async fn wait_for(page: &Page, js_condition: &str, timeout: Duration) -> Result<(), String> {
    let deadline = Instant::now() + timeout;
    loop {
        if let Ok(result) = page.evaluate(js_condition).await {
            if result.into_value::<bool>().unwrap_or(false) {
                return Ok(());
            }
        }
        if Instant::now() >= deadline {
            return Err(format!(
                "condition not met within {timeout:?}: {js_condition}"
            ));
        }
        tokio::time::sleep(Duration::from_millis(100)).await;
    }
}

/// Wait until the htmx library itself is loaded (CDN script tag).
async fn wait_for_htmx(page: &Page) {
    wait_for(page, "window.htmx !== undefined", SWAP_TIMEOUT)
        .await
        .expect("htmx did not load — the browser needs outbound HTTPS to cdn.jsdelivr.net");
}

/// Evaluate a JS expression and deserialize it as an integer.
async fn eval_int(page: &Page, expr: &str) -> Option<i64> {
    page.evaluate(expr)
        .await
        .ok()
        .and_then(|result| result.into_value::<i64>().ok())
}

/// Evaluate a JS expression and deserialize it as a string.
async fn eval_string(page: &Page, expr: &str) -> Option<String> {
    page.evaluate(expr)
        .await
        .ok()
        .and_then(|result| result.into_value::<String>().ok())
}

/// `innerHTML` of the first element matching `selector` (`""` when absent).
async fn inner_html(page: &Page, selector: &str) -> String {
    let script = format!(
        "document.querySelector({selector:?}) ? document.querySelector({selector:?}).innerHTML : ''"
    );
    eval_string(page, &script).await.unwrap_or_default()
}

// ---------------------------------------------------------------------------
// Seeding
// ---------------------------------------------------------------------------

fn seed_icon(store: &common::SharedStore, title: &str, url: &str, content: &str) {
    let mut store = store.lock().unwrap();
    store.icons.push(Icon {
        id: None,
        title: title.to_string(),
        url: url.to_string(),
        content: Some(content.to_string()),
    });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

/// Navigate to `/` and prove the three load-triggered htmx swaps happen in a
/// real browser: posts into `.page__content`, nav pages into `.pages_nav`,
/// footer icons into `.footer__links`.
#[tokio::test(flavor = "multi_thread")]
async fn index_load_triggers_real_htmx_swaps() {
    let (store, app) = test_app();
    seed_published_post(&store, "Browser E2E Post", "browser-e2e-post", "Body text.");
    seed_page(&store, "About", "about");
    seed_icon(&store, "github", "https://github.com/example", "gh");

    let (base_url, server) = serve(app.clone()).await;
    wait_for_server(&base_url).await;
    let mut browser = TestBrowser::launch().await;
    let page = browser.new_page().await;
    page.add_init_script(INSTRUMENT)
        .await
        .expect("install instrumentation");
    page.goto(format!("{base_url}/"))
        .await
        .expect("navigate to /");
    wait_for_htmx(&page).await;

    // The page rendered: `index.html` extends the layout with its default title.
    let title = eval_string(&page, "document.title")
        .await
        .unwrap_or_default();
    assert!(
        title.contains("Неразумный перфекционизм"),
        "unexpected page title: {title:?}"
    );

    // htmx must have swapped the posts listing into the initially-empty
    // `.page__content` div (index.html only contains an empty #posts div).
    wait_for(
        &page,
        "document.querySelector('.page__content .minipost__title') !== null",
        SWAP_TIMEOUT,
    )
    .await
    .expect("posts listing should be swapped into .page__content on load");

    let swaps = eval_int(&page, "window.__pageContentSwaps")
        .await
        .unwrap_or(0);
    assert!(
        swaps >= 1,
        "expected at least one htmx:afterSwap into .page__content, got {swaps}"
    );

    // Dual-mode consistency: the DOM that landed in the swap target carries
    // the same post and the same hx-get link as the fragment the server
    // returns for the identical HX-Request.
    let fragment = body_text(get_hx(&app, "/posts").await).await;
    assert!(fragment.contains("Browser E2E Post"));
    let dom = inner_html(&page, ".page__content").await;
    assert!(
        dom.contains("Browser E2E Post"),
        "swapped-in DOM misses the post title"
    );
    assert!(
        dom.contains("hx-get=\"/browser-e2e-post\""),
        "swapped-in DOM misses the hx-get link"
    );

    // The other two load-triggered swaps: nav pages and footer icons.
    wait_for(
        &page,
        "document.querySelector('.pages_nav a.nav__link') !== null",
        SWAP_TIMEOUT,
    )
    .await
    .expect("pages_nav should be populated by /hx/pages");
    let nav_text = eval_string(
        &page,
        "document.querySelector('.pages_nav') ? document.querySelector('.pages_nav').textContent : ''",
    )
    .await
    .unwrap_or_default();
    assert!(
        nav_text.contains("About"),
        "pages_nav should contain the About page"
    );

    wait_for(
        &page,
        "document.querySelector('.footer__links a') !== null",
        SWAP_TIMEOUT,
    )
    .await
    .expect("footer links should be populated by /hx/icons");
    let footer_text = eval_string(
        &page,
        "document.querySelector('.footer__links') ? document.querySelector('.footer__links').textContent : ''",
    )
    .await
    .unwrap_or_default();
    assert!(
        footer_text.contains("gh"),
        "footer links should contain the seeded icon"
    );

    browser.close().await;
    server.abort();
}

/// Click a post link in the listing and prove htmx swaps the post fragment
/// into `.page__content` and `hx-push-url` updates the address bar — without
/// a full page navigation.
#[tokio::test(flavor = "multi_thread")]
async fn click_post_link_swaps_fragment_and_pushes_url() {
    let (store, app) = test_app();
    seed_published_post(
        &store,
        "Click Me Post",
        "click-me-post",
        "## Swapped via click",
    );

    let (base_url, server) = serve(app.clone()).await;
    wait_for_server(&base_url).await;
    let mut browser = TestBrowser::launch().await;
    let page = browser.new_page().await;
    page.add_init_script(INSTRUMENT)
        .await
        .expect("install instrumentation");
    page.goto(format!("{base_url}/"))
        .await
        .expect("navigate to /");
    wait_for_htmx(&page).await;

    // Wait for the load-triggered listing, then click the post link.
    wait_for(
        &page,
        "document.querySelector('.minipost__title') !== null",
        SWAP_TIMEOUT,
    )
    .await
    .expect("posts listing should load on /");
    page.find_element(".minipost__title")
        .await
        .expect("find post link")
        .click()
        .await
        .expect("click post link");

    // The click must drive a *second* swap into `.page__content`. (A full
    // navigation would reset the counter via the init script, so this
    // assertion also proves htmx prevented the default anchor navigation.)
    wait_for(&page, "window.__pageContentSwaps >= 2", SWAP_TIMEOUT)
        .await
        .expect("click should trigger a second htmx swap into .page__content");
    wait_for(
        &page,
        "document.querySelector('.page__content .post__title') !== null",
        SWAP_TIMEOUT,
    )
    .await
    .expect("post fragment should be swapped in");
    wait_for(
        &page,
        "location.pathname === '/click-me-post'",
        SWAP_TIMEOUT,
    )
    .await
    .expect("hx-push-url should update the address bar");

    // The swapped-in post body contains the rendered markdown.
    let body = inner_html(&page, ".post__body").await;
    assert!(
        body.contains("<h2>Swapped via click</h2>"),
        "markdown should be rendered inside the swapped fragment, got: {body}"
    );

    // Dual-mode: same fragment the server returns for the HX-Request.
    let fragment = body_text(get_hx(&app, "/click-me-post").await).await;
    assert!(fragment.contains("Click Me Post"));
    assert!(fragment.contains("<h2>Swapped via click</h2>"));

    browser.close().await;
    server.abort();
}

/// Navigate directly to a post page and prove its load-triggered self-load
/// swap (`hx-get="/{alias}"` with `hx-trigger="load"`) replaces
/// `.page__content` with the htmx fragment.
#[tokio::test(flavor = "multi_thread")]
async fn post_page_self_load_swap_matches_fragment() {
    let (store, app) = test_app();
    seed_published_post(&store, "Self Load Post", "self-load-post", "## Self loaded");

    let (base_url, server) = serve(app.clone()).await;
    wait_for_server(&base_url).await;
    let mut browser = TestBrowser::launch().await;
    let page = browser.new_page().await;
    page.add_init_script(INSTRUMENT)
        .await
        .expect("install instrumentation");
    page.goto(format!("{base_url}/self-load-post"))
        .await
        .expect("navigate to post");
    wait_for_htmx(&page).await;

    // post.html renders the article server-side AND carries a load-triggered
    // `hx-get="/self-load-post"`; the swap counter proves the fragment
    // actually replaced the content (the static render alone would not bump it).
    wait_for(&page, "window.__pageContentSwaps >= 1", SWAP_TIMEOUT)
        .await
        .expect("self-load htmx swap should fire on the post page");

    let title = eval_string(
        &page,
        "document.querySelector('.post__title') ? document.querySelector('.post__title').textContent : ''",
    )
    .await
    .unwrap_or_default();
    assert_eq!(title.trim(), "Self Load Post");

    // The swapped-in fragment renders the same markdown the HX-Request
    // endpoint returns.
    let fragment = body_text(get_hx(&app, "/self-load-post").await).await;
    assert!(fragment.contains("Self Load Post"));
    assert!(fragment.contains("<h2>Self loaded</h2>"));

    let dom = inner_html(&page, ".page__content").await;
    assert!(
        dom.contains("<h2>Self loaded</h2>"),
        "swapped post body should render markdown, got: {dom}"
    );

    browser.close().await;
    server.abort();
}
