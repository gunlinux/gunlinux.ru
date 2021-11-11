# -*- coding: utf-8 -*-
import datetime
from flask import render_template, Blueprint, request
from sqlalchemy import or_
from pro import cache
from pro.models.post import Post

post = Blueprint("postb", __name__)

PAGE_STATUS = 1
PAGE_SPECIAL = 3


@post.route('/')
@cache.cached(timeout=50)
def index():
    conds = [Post.status > PAGE_STATUS]
    posts = Post.query.filter(
        or_(*conds)).order_by(Post.publishedon.desc()).all()
    pages = Post.query.filter_by(status=PAGE_STATUS).order_by(Post.id).all()
    return render_template("posts.html", posts=posts, pages=pages)


@post.route('/<alias>')
@cache.cached(timeout=50)
def view(alias=None):
    post = Post.query.filter(Post.alias == alias).filter(
        Post.status > 0).first_or_404()
    pages = Post.query.filter_by(status=PAGE_STATUS).order_by(Post.id).all()
    if post.status == PAGE_SPECIAL:
        return render_template('special.html', post=post, pages=pages)
    return render_template('post.html', post=post, pages=pages)


@post.route('/md/', methods=["POST", "GET"])
def getmd():
    post = request.form.get('data')
    return render_template('postmd.html', post=post)


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
    conds = [Post.status > PAGE_STATUS]
    date = datetime.datetime.now()
    list_posts = Post.query.filter(or_(*conds)).order_by(
        Post.publishedon.desc()).all()
    return render_template('rss.xml', posts=list_posts, date=date)
