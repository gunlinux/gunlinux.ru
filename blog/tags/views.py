import sqlalchemy as sa
from flask import Blueprint, render_template

from blog.post.views import pages_gen
from blog.repos.tag import TagRepository
from blog.services.tag import TagService
from blog.services.factory import ServiceFactory

tagsb = Blueprint("tagsb", __name__, url_prefix="/tags")


@tagsb.route("/")
@pages_gen
def index(**kwargs):
    # Use service layer instead of direct database access
    tag_service = ServiceFactory.create_tag_service()
    tags = tag_service.get_all_tags_orm()
    return render_template("tags.html", tags=tags, **kwargs)


@tagsb.route("/<alias>")
@pages_gen
def view(alias=None, **kwargs):
    # Use service layer instead of direct database access
    tag_service = ServiceFactory.create_tag_service()
    tag = tag_service.get_tag_by_alias_orm(alias)
    if not tag:
        from flask import abort
        abort(404)
    return render_template("posts.html", posts=tag.posts, tag=tag, **kwargs)
