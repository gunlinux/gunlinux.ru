import datetime

import pytest

from app.domain.post import Post
from app.domain.tag import Tag
from app.repositories.post import PostRepository
from app.repositories.tag import TagRepository


@pytest.mark.asyncio
async def test_published_post_view(client, db_session):
    repo = PostRepository(db_session)
    post = Post(
        pagetitle="My View Post",
        alias="my-view-post",
        content="# Hello",
        publishedon=datetime.datetime.now(),
    )
    await repo.create(post)
    await db_session.commit()

    response = await client.get("/my-view-post")
    assert response.status_code == 200
    assert "My View Post" in response.text


@pytest.mark.asyncio
async def test_unpublished_post_is_404(client, db_session):
    repo = PostRepository(db_session)
    post = Post(pagetitle="Draft", alias="draft-view-post", content="secret")
    await repo.create(post)
    await db_session.commit()

    response = await client.get("/draft-view-post")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_tag_view(client, db_session):
    repo = TagRepository(db_session)
    tag = Tag(title="Python", alias="python-view")
    await repo.create(tag)
    await db_session.commit()

    response = await client.get("/tags/python-view")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tag_not_found(client):
    response = await client.get("/tags/nonexistent-xyz")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_markdown_endpoint(client):
    response = await client.post("/md/", data={"data": "# Title"})
    assert response.status_code == 200
    assert "Title" in response.json()["data"]


@pytest.mark.asyncio
async def test_htmx_pages(client):
    response = await client.get("/hx/pages")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_htmx_icons(client):
    response = await client.get("/hx/icons")
    assert response.status_code == 200
