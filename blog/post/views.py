import datetime
from functools import wraps

import markdown
import sqlalchemy as sa
from flask import (
    Blueprint,
    current_app,
    jsonify,
    make_response,
    render_template,
    request,
)
from sqlalchemy import or_

from blog import cache, db
from blog.post.models import Post

post = Blueprint("postb", __name__)


def pages_gen(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        page_category = current_app.config["PAGE_CATEGORY"]
        pages_query = sa.select(Post).where(Post.category_id == page_category)
        pages = db.session.scalars(pages_query).all()
        return f(pages=pages, *args, **kwargs)

    return decorated_function


@post.route("/")
@cache.cached(timeout=50)
@pages_gen
def index(**kwargs):
    post_query = sa.select(Post).where(
        Post.publishedon.isnot(None),
        Post.category_id.is_(None),
    )
    posts = db.session.scalars(post_query).all()
    return render_template("posts.html", posts=posts, **kwargs)


@post.route("/<alias>")
@cache.cached(timeout=50)
@pages_gen
def view(alias=None, **kwargs):
    page_category = current_app.config["PAGE_CATEGORY"]
    post_query = sa.select(Post).where(
        or_(Post.publishedon.isnot(None), Post.category_id == page_category),
        Post.alias == alias,
    )
    post = db.first_or_404(post_query)
    return render_template("post.html", post=post, **kwargs)


@post.route("/md/", methods=["POST", "GET"])
def getmd():
    post_data = request.form.get("data", "")
    out = {"data": markdown.markdown(post_data)}
    return jsonify(out)


@post.route("/robots.txt")
@cache.cached(timeout=50)
def robots():
    return """
User-agent: *
Crawl-delay: 2
Disallow: /tag/*
Host: gunlinux.ru
"""


@post.route("/rss.xml")
@cache.cached(timeout=50)
def rss():
    date = datetime.datetime.now()
    post_query = sa.select(Post).where(
        Post.publishedon.isnot(None),
        Post.category_id.is_(None),
    )
    list_posts = db.session.scalars(post_query).all()
    rss_xml = render_template("rss.xml", posts=list_posts, date=date)
    response = make_response(rss_xml)
    response.headers["Content-Type"] = "application/rss+xml"
    return response
