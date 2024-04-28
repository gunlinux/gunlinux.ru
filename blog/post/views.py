import datetime
import markdown
from flask import jsonify, render_template, Blueprint, request, make_response, current_app
import sqlalchemy as sa
from blog import cache, db
from blog.post.models import Post

post = Blueprint("postb", __name__)

PAGE_STATUS = 1
PAGE_SPECIAL = 3


@post.route('/')
@cache.cached(timeout=50)
def index():
    page_category = current_app.config['PAGE_CATEGORY']
    post_query = sa.select(Post).where(Post.publishedon != None,
                                       Post.category_id == None)
    posts = db.session.scalars(post_query).all()
    pages_query = sa.select(Post).where(Post.category_id == page_category)
    pages = db.session.scalars(pages_query).all()

    return render_template("posts.html", posts=posts, pages=pages)


@post.route('/<alias>')
@cache.cached(timeout=50)
def view(alias=None):
    post_query = sa.select(Post).where(Post.publishedon != None, Post.alias == alias)
    post = db.first_or_404(post_query)
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
    post_query = sa.select(Post).where(Post.publishedon != None,
                                       Post.category_id == None)
    list_posts = db.session.scalars(post_query).all()
    rss_xml = render_template('rss.xml', posts=list_posts, date=date)
    response = make_response(rss_xml)
    response.headers['Content-Type'] = 'application/rss+xml'
    return response
