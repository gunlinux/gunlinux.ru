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


@pytest.mark.asyncio
async def test_post_crud(db_session):
    repo = PostRepository(db_session)
    post = Post(pagetitle="Test Post", alias="test-post-repo", content="content")
    created = await repo.create(post)
    assert created.id is not None

    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.pagetitle == "Test Post"

    fetched_alias = await repo.get_by_alias("test-post-repo")
    assert fetched_alias is not None

    all_posts = await repo.get_all()
    assert any(p.alias == "test-post-repo" for p in all_posts)

    assert await repo.delete(created.id) is True


@pytest.mark.asyncio
async def test_post_published(db_session):
    repo = PostRepository(db_session)
    post = Post(
        pagetitle="Published",
        alias="published-repo",
        content="x",
        publishedon=datetime.datetime.now(),
    )
    await repo.create(post)
    published = await repo.get_published_posts()
    assert any(p.alias == "published-repo" for p in published)


@pytest.mark.asyncio
async def test_tag_crud(db_session):
    repo = TagRepository(db_session)
    tag = Tag(title="Python", alias="python-repo")
    created = await repo.create(tag)
    assert created.id is not None

    assert (await repo.get_by_id(created.id)) is not None
    assert (await repo.get_by_alias("python-repo")) is not None
    assert await repo.delete(created.id) is True


@pytest.mark.asyncio
async def test_user_crud(db_session):
    repo = UserRepository(db_session)
    user = User(name="repouser", password=pwd_context.hash("pass123"))
    created = await repo.create(user)
    assert created.id is not None
    assert (await repo.get_by_name("repouser")) is not None


@pytest.mark.asyncio
async def test_user_authenticate(db_session):
    repo = UserRepository(db_session)
    user = User(name="authrepo", password=pwd_context.hash("secret"))
    await repo.create(user)

    assert await repo.authenticate("authrepo", "secret") is not None
    assert await repo.authenticate("authrepo", "wrong") is None


@pytest.mark.asyncio
async def test_category_crud(db_session):
    repo = CategoryRepository(db_session)
    cat = Category(title="Tech", alias="tech-repo", page=False)
    created = await repo.create(cat)
    assert created.id is not None
    assert (await repo.get_by_alias("tech-repo")) is not None


@pytest.mark.asyncio
async def test_icon_crud(db_session):
    repo = IconRepository(db_session)
    icon = Icon(title="GitHub-repo", url="https://github.com/repo", content="<svg/>")
    created = await repo.create(icon)
    assert created.id is not None
    assert (await repo.get_by_title("GitHub-repo")) is not None
    assert len(await repo.get_all()) >= 1
