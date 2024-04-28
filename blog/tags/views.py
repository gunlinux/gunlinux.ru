import sqlalchemy as sa
from flask import render_template, Blueprint, current_app
from blog.post.models import Post
from blog.tags.models import Tag
from blog import db

tagsb = Blueprint("tagsb", __name__, url_prefix='/tags')

PAGE_STATUS = 1
PAGE_SPECIAL = 3


@tagsb.route('/')
def index():
    page_category = current_app.config['PAGE_CATEGORY']
    tags = db.session.scalars(sa.select(Tag)).all()
    pages_query = sa.select(Post).where(Post.category_id == page_category)
    pages = db.session.scalars(pages_query).all()
    return render_template("tags.html", tags=tags, pages=pages)


@tagsb.route('/<alias>')
def view(alias=None):
    page_category = current_app.config['PAGE_CATEGORY']
    pages_query = sa.select(Post).where(Post.category_id == page_category)
    pages = db.session.scalars(pages_query).all()
    tag_query = sa.select(Tag).where(Tag.alias == alias)
    tag = db.first_or_404(tag_query)
    return render_template('posts.html', posts=tag.posts, pages=pages, tag=tag)
