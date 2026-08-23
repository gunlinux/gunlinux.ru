//! PostgreSQL scratch-database provisioning for the parity suite (feature
//! `postgres-parity`, plan.md §3 Thread A).
//!
//! Postgres 16 is resolved from `TEST_DATABASE_URL` when set (GitHub Actions
//! service container), otherwise a `postgres:16` container is started via
//! testcontainers. [`provision`] creates a uniquely-named scratch database and
//! applies the baseline migration with the real [`Migrator`] — which is also
//! what verifies `m20260101_000001_create_schema` is Postgres-correct
//! (plan.md risk §5.4).
//!
//! One container per test (rather than a shared static): the container handle
//! is owned by [`TestDb`] so its `Drop` deterministically removes the
//! container when the test finishes — a `static` would never run `Drop` and
//! would leak a container per test run.

use std::str::FromStr;

use persistence::migrator::{Migrator, MigratorTrait};
use persistence::pool;
use sea_orm::sqlx::postgres::PgConnectOptions;
use sea_orm::sqlx::{ConnectOptions, PgPool};
use sea_orm::DatabaseConnection;
use testcontainers::ContainerAsync;
use testcontainers::GenericImage;

static SCRATCH_COUNTER: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);

/// A migrated scratch database plus the resources that must outlive the test.
pub struct TestDb {
    pub db: DatabaseConnection,
    pub admin: PgPool,
    pub scratch: String,
    /// Kept alive for the test's lifetime; removed on drop.
    _container: Option<ContainerAsync<GenericImage>>,
}

/// Provision a scratch database: resolve Postgres, create the database, and
/// apply the baseline migration.
pub async fn provision() -> TestDb {
    let (admin_url, container) = match std::env::var("TEST_DATABASE_URL") {
        Ok(url) => (url, None),
        Err(_) => {
            let (url, container) = start_container().await;
            (url, Some(container))
        }
    };

    let n = SCRATCH_COUNTER.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
    let scratch = format!("parity_{}_{}", std::process::id(), n);
    let admin_opts = PgConnectOptions::from_str(&admin_url).expect("parse postgres admin URL");
    let admin = connect_admin(&admin_opts).await;
    // CREATE DATABASE cannot run inside a transaction; a bare sqlx query runs
    // as a single statement, which is fine.
    sea_orm::sqlx::query(&format!("CREATE DATABASE \"{scratch}\""))
        .execute(&admin)
        .await
        .expect("create scratch database");
    let scratch_url = admin_opts.database(&scratch).to_url_lossy().to_string();
    let db = pool::connect(&scratch_url)
        .await
        .expect("connect to scratch database");
    Migrator::up(&db, None)
        .await
        .expect("apply baseline migration to scratch Postgres database");

    TestDb {
        db,
        admin,
        scratch,
        _container: container,
    }
}

/// Connect to the admin database, retrying through the `postgres` image's
/// init-phase restart: the entrypoint briefly runs a *temporary* server (which
/// logs "ready to accept connections") and then restarts the real one, so the
/// first connection often lands in the shutdown window.
async fn connect_admin(opts: &PgConnectOptions) -> PgPool {
    use std::time::Duration;

    let mut last_err: Option<sea_orm::sqlx::Error> = None;
    for _ in 0..30 {
        match PgPool::connect_with(opts.clone()).await {
            Ok(pool) => {
                // Confirm the server is stable before returning the pool.
                match sea_orm::sqlx::query("SELECT 1").execute(&pool).await {
                    Ok(_) => return pool,
                    Err(e) => last_err = Some(e),
                }
            }
            Err(e) => last_err = Some(e),
        }
        tokio::time::sleep(Duration::from_millis(500)).await;
    }
    panic!(
        "connect to postgres admin database: {}",
        last_err
            .map(|e| e.to_string())
            .unwrap_or_else(|| "gave up after 30 attempts".into())
    );
}

/// Tear down in dependency order: close the app connection, drop the scratch
/// database, then remove the container (via `_container`'s `Drop`).
pub async fn cleanup(test_db: TestDb) {
    let TestDb {
        db,
        admin,
        scratch,
        _container,
    } = test_db;
    db.close().await.ok();
    let _ = sea_orm::sqlx::query(&format!(
        "DROP DATABASE IF EXISTS \"{scratch}\" WITH (FORCE)"
    ))
    .execute(&admin)
    .await;
    drop(_container);
    drop(admin);
}

/// Start a `postgres:16` container and return its admin URL.
async fn start_container() -> (String, ContainerAsync<GenericImage>) {
    use testcontainers::core::IntoContainerPort;
    use testcontainers::core::WaitFor;
    use testcontainers::runners::AsyncRunner;
    use testcontainers::ImageExt;

    // `with_exposed_port`/`with_wait_for` are inherent GenericImage methods;
    // no explicit host port is requested, so Docker publishes the exposed
    // port on a random free host port (publish_all_ports) and
    // `get_host_port_ipv4` reports the actual mapping.
    let image = GenericImage::new("postgres", "16")
        .with_exposed_port(5432.tcp())
        .with_wait_for(WaitFor::message_on_stdout(
            "database system is ready to accept connections",
        ));
    let container = image
        .with_env_var("POSTGRES_PASSWORD", "postgres")
        .start()
        .await
        .expect("start postgres:16 testcontainer");
    let host = container.get_host().await.expect("postgres container host");
    let port = container
        .get_host_port_ipv4(5432.tcp())
        .await
        .expect("postgres container port");
    let url = format!("postgres://postgres:postgres@{host}:{port}/postgres");
    (url, container)
}
