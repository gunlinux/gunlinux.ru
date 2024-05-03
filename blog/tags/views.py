import sqlalchemy as sa
from flask import render_template, Blueprint
from blog.post.views import pages_gen
from blog.tags.models import Tag
from blog import db

tagsb = Blueprint("tagsb", __name__, url_prefix="/tags")


@tagsb.route("/")
@pages_gen
def index(**kwargs):
    tags = db.session.scalars(sa.select(Tag)).all()
    return render_template("tags.html", tags=tags, **kwargs)


@tagsb.route("/<alias>")
@pages_gen
def view(alias=None, **kwargs):
    tag_query = sa.select(Tag).where(Tag.alias == alias)
    tag = db.first_or_404(tag_query)
    return render_template("posts.html", posts=tag.posts, tag=tag, **kwargs)
