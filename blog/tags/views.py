from flask import render_template, Blueprint
from blog.post.models import Post
from blog.tags.models import Tag

tagsb = Blueprint("tagsb", __name__, url_prefix='/tags')

PAGE_STATUS = 1
PAGE_SPECIAL = 3


@tagsb.route('/')
def index():
    tags = Tag.query.all()
    pages = Post.query.filter_by(status=PAGE_STATUS).order_by(Post.id).all()
    return render_template("tags.html", tags=tags, pages=pages)


@tagsb.route('/<alias>')
def view(alias=None):
    tag = Tag.query.filter(Tag.alias == alias).first_or_404()
    pages = Post.query.filter_by(status=PAGE_STATUS).order_by(Post.id).all()
    return render_template('posts.html', posts=tag.posts, pages=pages, tag=tag)
