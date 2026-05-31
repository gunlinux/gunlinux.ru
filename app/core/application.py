from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from starlette.middleware.sessions import SessionMiddleware

from app.core.settings import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    FastAPICache.init(InMemoryBackend())
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="gunlinux.ru",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )

    app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

    # Static files
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    # Routers — register prefixed routers before posts, whose catch-all
    # GET /{alias} would otherwise shadow single-segment paths.
    from app.api.posts import router as posts_router
    from app.api.tags import router as tags_router

    app.include_router(tags_router)
    app.include_router(posts_router)

    # Admin
    from app.admin import create_admin
    from app.infrastructure.session import engine

    create_admin(app, engine)

    return app
