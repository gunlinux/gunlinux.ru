import datetime

import markdown
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi_cache.decorator import cache

from app.core.cache import ResponseCoder, htmx_key_builder
from app.core.dependencies import IconServiceDep, PostServiceDep
from app.core.templates import templates

router = APIRouter()


@router.get("/")
@cache(expire=50, coder=ResponseCoder, key_builder=htmx_key_builder)
async def index(request: Request) -> Response:
    return templates.TemplateResponse(request, "index.html")


@router.get("/posts")
@cache(expire=50, coder=ResponseCoder, key_builder=htmx_key_builder)
async def posts(request: Request, post_service: PostServiceDep) -> Response:
    all_posts = await post_service.get_all_published_content()
    is_htmx = bool(request.headers.get("HX-Request"))
    template = "posts.htmx" if is_htmx else "posts.html"
    return templates.TemplateResponse(request, template, {"posts": all_posts})


@router.get("/hx/pages")
@cache(expire=50, coder=ResponseCoder, key_builder=htmx_key_builder)
async def pages_hx(request: Request, post_service: PostServiceDep) -> Response:
    pages = await post_service.get_page_posts()
    return templates.TemplateResponse(request, "pages.htmx", {"pages": pages})


@router.get("/hx/icons")
@cache(expire=50, coder=ResponseCoder, key_builder=htmx_key_builder)
async def icons_hx(request: Request, icon_service: IconServiceDep) -> Response:
    icons = await icon_service.get_all_icons()
    return templates.TemplateResponse(request, "icons/icons.htmx", {"icons": icons})


@router.get("/robots.txt")
@cache(expire=50, coder=ResponseCoder)
async def robots() -> Response:
    content = "\nUser-agent: *\nCrawl-delay: 2\nDisallow: /tags/*\nHost: gunlinux.ru\n"
    return Response(content=content, media_type="text/plain")


@router.get("/sitemap.xml")
async def sitemap(post_service: PostServiceDep) -> Response:
    pages = await post_service.get_page_posts()
    posts_list = await post_service.get_published_posts()
    urls = [f"<url><loc>/{p.alias}</loc></url>" for p in (*pages, *posts_list)]
    header = '<?xml version="1.0" encoding="UTF-8"?>'
    ns = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    xml = header + ns + "".join(urls) + "</urlset>"
    return Response(content=xml, media_type="application/xml")


@router.get("/rss.xml")
@cache(expire=50, coder=ResponseCoder)
async def rss(request: Request, post_service: PostServiceDep) -> Response:
    posts_list = await post_service.get_published_posts()
    date = datetime.datetime.now()
    rendered = templates.TemplateResponse(
        request, "rss.xml", {"posts": posts_list, "date": date}
    )
    return Response(content=rendered.body, media_type="application/rss+xml")


@router.post("/md/")
async def getmd(request: Request) -> JSONResponse:
    form = await request.form()
    post_data = str(form.get("data", ""))
    return JSONResponse({"data": markdown.markdown(post_data)})


@router.get("/{alias}")
@cache(expire=50, coder=ResponseCoder, key_builder=htmx_key_builder)
async def post_view(
    alias: str, request: Request, post_service: PostServiceDep
) -> Response:
    post = await post_service.get_post_by_alias(alias)
    if not post:
        raise HTTPException(status_code=404)

    is_published = post.publishedon is not None
    if not (is_published or post.is_page):
        raise HTTPException(status_code=404)

    tags = await post_service.get_tags_for_post(post.id) if post.id else []
    is_htmx = bool(request.headers.get("HX-Request"))
    template = "post.htmx" if is_htmx else "post.html"
    return templates.TemplateResponse(request, template, {"post": post, "tags": tags})
