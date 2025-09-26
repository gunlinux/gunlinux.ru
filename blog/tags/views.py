from typing import TYPE_CHECKING, ParamSpecKwargs

from flask import Blueprint, render_template, Response

from blog.post.views import pages_gen
from blog.services.factory import ServiceFactory

if TYPE_CHECKING:
    from flask import Response

tags = Blueprint("tags", __name__, url_prefix="/tags")


@tags.route("/")
@pages_gen
def index(**kwargs: ParamSpecKwargs) -> Response | str:
    tag_service = ServiceFactory.create_tag_service()
    tags = tag_service.get_all_tags()
    return render_template("tags.html", tags=tags, **kwargs)


@tags.route("/<alias>")
@pages_gen
def view(alias: str | None = None, **kwargs: ParamSpecKwargs) -> Response | str:
    if alias is None:
        from flask import abort

        abort(404)

    tag_service = ServiceFactory.create_tag_service()
    tag = tag_service.get_tag_by_alias(alias)
    if not tag:
        from flask import abort

        abort(404)

    # Get posts for this tag through the post service
    post_service = ServiceFactory.create_post_service()
    posts = post_service.get_posts_by_tag(tag.id) if tag.id else []
    return render_template("posts.html", posts=posts, tag=tag, **kwargs)
