from fastapi import APIRouter, HTTPException, Request, Response

from app.core.dependencies import PostServiceDep, TagServiceDep
from app.core.templates import templates

router = APIRouter(prefix="/tags")


@router.get("")
@router.get("/")
async def tags_index(request: Request, tag_service: TagServiceDep) -> Response:
    tags = await tag_service.get_all_tags()
    is_htmx = bool(request.headers.get("HX-Request"))
    template = "tags.htmx" if is_htmx else "tags.html"
    return templates.TemplateResponse(request, template, {"tags": tags})


@router.get("/{alias}")
async def tag_view(
    alias: str,
    request: Request,
    tag_service: TagServiceDep,
    post_service: PostServiceDep,
) -> Response:
    tag = await tag_service.get_tag_by_alias(alias)
    if not tag:
        raise HTTPException(status_code=404)
    posts = await post_service.get_posts_by_tag(tag.id) if tag.id else []
    is_htmx = bool(request.headers.get("HX-Request"))
    template = "posts.htmx" if is_htmx else "tag.html"
    return templates.TemplateResponse(request, template, {"posts": posts, "tag": tag})
