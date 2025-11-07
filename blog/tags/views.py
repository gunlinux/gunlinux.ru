from typing import TYPE_CHECKING

from flask import Blueprint, render_template, Response, abort, request

from blog.services.factory import ServiceFactory

if TYPE_CHECKING:
    from flask import Response

tags = Blueprint("tags", __name__, url_prefix="/tags")


@tags.route("/")
def index() -> Response | str:
    template = "tags.htmx" if request.args.get("hx") else "tags.html"
    tag_service = ServiceFactory.create_tag_service()
    tags = tag_service.get_all_tags()
    return render_template(template, tags=tags)


@tags.route("/<alias>")
def view(alias: str | None = None) -> Response | str:
    template = "posts.htmx" if request.args.get("hx") else "tag.html"
    if alias is None:
        abort(404)

    tag_service = ServiceFactory.create_tag_service()
    tag = tag_service.get_tag_by_alias(alias)
    if not tag:
        abort(404)

    # Get posts for this tag through the post service
    post_service = ServiceFactory.create_post_service()
    posts = post_service.get_posts_by_tag(tag.id) if tag.id else []
    return render_template(template, posts=posts, tag=tag)
