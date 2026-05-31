import datetime

import pytest

from app.domain.category import Category
from app.domain.icon import Icon
from app.domain.post import Post
from app.domain.tag import Tag
from app.domain.user import User
from app.models.user import pwd_context
from app.repositories.category import CategoryRepository
from app.repositories.icon import IconRepository
from app.repositories.post import PostRepository
from app.repositories.tag import TagRepository
from app.repositories.user import UserRepository
from app.services.category import CategoryService
from app.services.icon import IconService
from app.services.post import PostService
from app.services.tag import TagService
from app.services.user import UserService


@pytest.mark.asyncio
async def test_post_service_crud(db_session):
    svc = PostService(PostRepository(db_session))
    post = Post(pagetitle="Hello", alias="hello-svc", content="world")
    created = await svc.create_post(post)
    assert created.id is not None

    assert (await svc.get_post_by_alias("hello-svc")) is not None
    assert any(p.alias == "hello-svc" for p in await svc.get_all_posts())


@pytest.mark.asyncio
async def test_post_service_published(db_session):
    svc = PostService(PostRepository(db_session))
    post = Post(
        pagetitle="Pub",
        alias="pub-svc",
        content="x",
        publishedon=datetime.datetime.now(),
    )
    await svc.create_post(post)
    published = await svc.get_published_posts()
    assert any(p.alias == "pub-svc" for p in published)


@pytest.mark.asyncio
async def test_tag_service_crud(db_session):
    svc = TagService(TagRepository(db_session))
    tag = Tag(title="FastAPI", alias="fastapi-svc")
    created = await svc.create_tag(tag)
    assert created.id is not None
    assert (await svc.get_tag_by_alias("fastapi-svc")) is not None


@pytest.mark.asyncio
async def test_user_service_auth(db_session):
    svc = UserService(UserRepository(db_session))
    user = User(name="svcauth", password=pwd_context.hash("pass"))
    await svc.create_user(user)

    assert await svc.authenticate_user("svcauth", "pass") is not None
    assert await svc.authenticate_user("svcauth", "bad") is None


@pytest.mark.asyncio
async def test_category_service_crud(db_session):
    svc = CategoryService(CategoryRepository(db_session))
    cat = Category(title="Pages", alias="pages-svc", page=True)
    created = await svc.create_category(cat)
    assert created.id is not None
    assert (await svc.get_category_by_alias("pages-svc")) is not None


@pytest.mark.asyncio
async def test_icon_service_crud(db_session):
    svc = IconService(IconRepository(db_session))
    icon = Icon(title="Twitter-svc", url="https://twitter.com/svc", content="<svg/>")
    created = await svc.create_icon(icon)
    assert created.id is not None
    assert (await svc.get_icon_by_title("Twitter-svc")) is not None
    assert len(await svc.get_all_icons()) >= 1
