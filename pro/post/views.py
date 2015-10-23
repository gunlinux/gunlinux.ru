# -*- coding: utf-8 -*-
import datetime
from flask import render_template, Blueprint, request
from sqlalchemy import or_
from pro.models.post import Post

post = Blueprint("postb", __name__)


@post.route('/')
def index():
    conds = [Post.status == '1', Post.status == '2', Post.status == '4']
    posts = Post.query.filter(
        or_(*conds)).order_by(Post.publishedon.desc()).all()
    pages = Post.query.filter_by(status=3).order_by(Post.id).all()
    return render_template(
        "posts.html",
        posts=posts,
        pages=pages)


@post.route('/works')
def works():
    pages = Post.query.filter_by(status=3).order_by(Post.id).all()
    return render_template('works.html', pages=pages)


@post.route('/<alias>')
def view(alias=None):
    post = Post.query.filter(Post.alias == alias).filter(
        Post.status > 0).first_or_404()
    pages = Post.query.filter_by(status=3).order_by(Post.id).all()
    if post.status == 4:
        return render_template('special.html', post=post, pages=pages)
    return render_template('post.html', post=post, pages=pages)


@post.route('/md/', methods=["POST", "GET"])
def getmd():
    post = request.form.get('data')
    return render_template('postmd.html', post=post)


@post.route('/robots.txt')
def robots():
    return '''
User-agent: *
Crawl-delay: 2
Disallow: /tag/*
Host: gunlinux.org
'''


@post.route('/rss.xml')
def rss():
    conds = [Post.status == '1', Post.status == '2', Post.status == '4']
    date = datetime.datetime.now()
    list_posts = Post.query.filter(or_(*conds)).order_by(
        Post.publishedon.desc()).all()
    return render_template('rss.xml', posts=list_posts, date=date)
