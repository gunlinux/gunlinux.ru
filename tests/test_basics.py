import pytest


@pytest.mark.asyncio
async def test_index(client):
    response = await client.get("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_posts(client):
    response = await client.get("/posts")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tags(client):
    response = await client.get("/tags/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_robots(client):
    response = await client.get("/robots.txt")
    assert response.status_code == 200
    assert "User-agent" in response.text


@pytest.mark.asyncio
async def test_rss(client):
    response = await client.get("/rss.xml")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_sitemap(client):
    response = await client.get("/sitemap.xml")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_login_form(client):
    response = await client.get("/auth/login")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_404(client):
    response = await client.get("/nonexistent-alias-xyz")
    assert response.status_code == 404
