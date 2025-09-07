from flask import Blueprint, render_template

from blog.post.views import pages_gen
from blog.services.factory import ServiceFactory

tagsb = Blueprint("tagsb", __name__, url_prefix="/tags")


@tagsb.route("/")
@pages_gen
def index(**kwargs):
    # Use service layer for domain models
    tag_service = ServiceFactory.create_tag_service()
    tags = tag_service.get_all_tags()
    return render_template("tags.html", tags=tags, **kwargs)


@tagsb.route("/<alias>")
@pages_gen
def view(alias=None, **kwargs):
    # Use service layer for domain models
    if alias is None:
        from flask import abort

        abort(404)

    tag_service = ServiceFactory.create_tag_service()
    tag = tag_service.get_tag_by_alias(alias)
    if not tag:
        from flask import abort

        abort(404)
    return render_template("posts.html", posts=tag.posts, tag=tag, **kwargs)
