import datetime
from typing import cast, ParamSpec, TypeVar

import markdown
from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    make_response,
    render_template,
    request,
    url_for,
    abort,
)


from blog.extensions import flask_sitemap, cache
from blog.services.factory import ServiceFactory

post = Blueprint("post", __name__)


P = ParamSpec("P")
R = TypeVar("R")


@post.route("/")
@cache.cached(timeout=50)  # pyright: ignore[reportUntypedFunctionDecorator]
def index(**kwargs: str) -> Response | str:
    return render_template("index.html", **kwargs)


@post.route("/posts")
@cache.cached(timeout=50)  # pyright: ignore[reportUntypedFunctionDecorator]
def posts(**kwargs: str) -> Response | str:
    post_service = ServiceFactory.create_post_service()
    posts = post_service.get_published_posts()
    return render_template("posts.html", posts=posts, **kwargs)


@post.route("/hx/pages")
@cache.cached(timeout=50)  # pyright: ignore[reportUntypedFunctionDecorator]
def pages_hx() -> Response | str:
    page_category = cast("list[int]", current_app.config["PAGE_CATEGORY"])
    post_service = ServiceFactory.create_post_service()
    pages = post_service.get_page_posts(page_category)
    return render_template("pages.htmx", pages=pages)


@post.route("/hx/icons")
@cache.cached(timeout=50)  # pyright: ignore[reportUntypedFunctionDecorator]
def icons_hx() -> Response | str:
    icon_service = ServiceFactory.create_icon_service()
    icons = icon_service.get_all_icons()
    return render_template("icons/icons.htmx", icons=icons)


@post.route("/<alias>")
@cache.cached(timeout=50)  # pyright: ignore[reportUntypedFunctionDecorator]
def view(alias: str | None = None, **kwargs: str) -> Response | str:
    template = "post.htmx" if request.args.get("hx") else "post.html"
    if alias is None:
        abort(404)

    post_service = ServiceFactory.create_post_service()
    post = post_service.get_post_by_alias(alias)
    if not post:
        abort(404)

    # For page categories, we need to check if it's a page or a regular post
    page_categories = cast("list[int]", current_app.config["PAGE_CATEGORY"])
    is_page = post.category_id is not None and post.category_id in page_categories
    is_published = post.publishedon is not None

    if not (is_published or is_page):
        abort(404)

    # Get tags for the post
    tags = post_service.get_tags_for_post(post.id) if post.id else []

    page_category_obj = None
    if post.category_id:
        category_service = ServiceFactory.create_category_service()
        page_category_obj = category_service.get_category_by_id(post.category_id)

    if page_category_obj and page_category_obj.template:
        return render_template(template, post=post, tags=tags, **kwargs)
    return render_template(template, post=post, tags=tags, **kwargs)


@flask_sitemap.register_generator
def site_map_gen():
    page_category = cast("list[int]", current_app.config["PAGE_CATEGORY"])

    post_service = ServiceFactory.create_post_service()
    pages = post_service.get_page_posts(page_category)
    for page in pages:
        yield url_for("post.view", alias=page.alias)

    posts = post_service.get_published_posts()
    for post in posts:
        yield url_for("post.view", alias=post.alias)


@post.route("/md/", methods=["POST", "GET"])
def getmd():
    post_data = request.form.get("data", "")
    out = {"data": markdown.markdown(post_data)}
    return jsonify(out)


@post.route("/robots.txt")
@cache.cached(timeout=50)  # pyright: ignore[reportUntypedFunctionDecorator]
def robots() -> Response | str:
    response = make_response(
        """\nUser-agent: *\nCrawl-delay: 2\nDisallow: /tag/*\nHost: gunlinux.ru\n"""
    )
    response.headers["Content-Type"] = "text/plain"
    return response


@post.route("/rss.xml")
@cache.cached(timeout=50)  # pyright: ignore[reportUntypedFunctionDecorator]
def rss():
    post_service = ServiceFactory.create_post_service()
    list_posts = post_service.get_published_posts()

    date = datetime.datetime.now()
    rss_xml = render_template("rss.xml", posts=list_posts, date=date)
    response = make_response(rss_xml)
    response.headers["Content-Type"] = "application/rss+xml"
    return response
