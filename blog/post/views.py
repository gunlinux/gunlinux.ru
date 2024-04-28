import datetime
import markdown
from flask import jsonify, render_template, Blueprint, request, make_response
import sqlalchemy as sa
from blog import cache, db
from blog.post.models import Post

post = Blueprint("postb", __name__)

PAGE_STATUS = 1
PAGE_SPECIAL = 3


@post.route('/')
@cache.cached(timeout=50)
def index():
    post_query = sa.select(Post).where(Post.status > PAGE_STATUS)
    posts = db.session.scalars(post_query).all()
    pages_query = sa.select(Post).where(Post.status == PAGE_STATUS)
    pages = db.session.scalars(pages_query).all()
    return render_template("posts.html", posts=posts, pages=pages)


@post.route('/<alias>')
@cache.cached(timeout=50)
def view(alias=None):
    post = Post.query.filter(Post.alias == alias).filter(Post.status > 0).first_or_404()
    pages_query = sa.select(Post).where(Post.status == PAGE_STATUS)
    pages = db.session.scalars(pages_query).all()

    return render_template('post.html', post=post, pages=pages)


@post.route('/md/', methods=["POST", "GET"])
def getmd():
    post_data = request.form.get('data', '')
    out = {
        "data": markdown.markdown(post_data)
    }
    return jsonify(out)


@post.route('/robots.txt')
@cache.cached(timeout=50)
def robots():
    return '''
User-agent: *
Crawl-delay: 2
Disallow: /tag/*
Host: gunlinux.ru
'''


@post.route('/rss.xml')
@cache.cached(timeout=50)
def rss():
    date = datetime.datetime.now()
    list_posts = Post.query.filter(Post.status >= PAGE_SPECIAL).order_by(
        Post.publishedon.desc()).all()
    rss_xml = render_template('rss.xml', posts=list_posts, date=date)
    response = make_response(rss_xml)
    response.headers['Content-Type'] = 'application/rss+xml'
    return response
