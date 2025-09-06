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
    url_for,
)
from blog.extensions import flask_sitemap

from blog import cache, db
from blog.post.models import Post, Icon
from blog.repos.post import PostRepository
from blog.repos.category import CategoryRepository
from blog.repos.icon import IconRepository
from blog.services.post import PostService
from blog.services.category import CategoryService
from blog.services.icon import IconService

post = Blueprint("postb", __name__)


def pages_gen(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Use service layer instead of direct database access
        from blog.services.factory import ServiceFactory
        
        page_category = current_app.config["PAGE_CATEGORY"]
        
        # Get posts using PostService
        post_service = ServiceFactory.create_post_service()
        pages = post_service.get_page_posts_orm(page_category)

        # Get icons using IconService
        icon_service = ServiceFactory.create_icon_service()
        icons = icon_service.get_all_icons_orm()

        return f(pages=pages, icons=icons, *args, **kwargs)

    return decorated_function


@post.route("/")
@cache.cached(timeout=50)
@pages_gen
def index(**kwargs):
    # Use service layer instead of direct database access
    from blog.services.factory import ServiceFactory
    
    post_service = ServiceFactory.create_post_service()
    posts = post_service.get_published_posts_orm()
    return render_template("posts.html", posts=posts, **kwargs)


@post.route("/<alias>")
@cache.cached(timeout=50)
@pages_gen
def view(alias=None, **kwargs):
    # Use service layer instead of direct database access
    from blog.services.factory import ServiceFactory
    
    post_service = ServiceFactory.create_post_service()
    post = post_service.get_post_by_alias_orm(alias)
    if not post:
        # Handle 404 case
        from flask import abort

        abort(404)

    # For page categories, we need to check if it's a page or a regular post
    page_categories = current_app.config["PAGE_CATEGORY"]
    is_page = post.category_id is not None and post.category_id in page_categories
    is_published = post.publishedon is not None

    if not (is_published or is_page):
        from flask import abort

        abort(404)

    # Load category object if needed using service layer
    page_category_obj = None
    if post.category_id:
        from blog.category.models import Category
        
        # Use CategoryService instead of direct database access
        category_service = ServiceFactory.create_category_service()
        page_category_obj = category_service.get_category_by_id_orm(post.category_id)

    if page_category_obj and page_category_obj.template:
        return render_template(page_category_obj.template, post=post, **kwargs)
    return render_template("post.html", post=post, **kwargs)


@flask_sitemap.register_generator
def site_map_gen():
    # Use service layer instead of direct database access
    from blog.services.factory import ServiceFactory
    
    page_category = current_app.config["PAGE_CATEGORY"]
    
    # Get pages using PostService
    post_service = ServiceFactory.create_post_service()
    pages = post_service.get_page_posts_orm(page_category)
    for page in pages:
        yield url_for("postb.view", alias=page.alias)
    
    # Get posts using PostService
    posts = post_service.get_published_posts_orm()
    for post in posts:
        yield url_for("postb.view", alias=post.alias)


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
    # Use service layer instead of direct database access
    from blog.services.factory import ServiceFactory
    
    post_service = ServiceFactory.create_post_service()
    list_posts = post_service.get_published_posts_orm()
    
    date = datetime.datetime.now()
    rss_xml = render_template("rss.xml", posts=list_posts, date=date)
    response = make_response(rss_xml)
    response.headers["Content-Type"] = "application/rss+xml"
    return response
