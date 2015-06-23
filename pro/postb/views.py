# -*- coding: utf-8 -*-
import datetime
from flask import render_template
from sqlalchemy import or_
from .models import Post
from . import postb


@postb.route('/')
def index():
    conds = [Post.status == '1', Post.status == '2']
    posts = Post.query.filter(
        or_(*conds)).order_by(Post.publishedon.desc()).all()
    pages = Post.query.filter_by(status=3).order_by(Post.id).all()
    return render_template(
        "posts.html",
        posts=posts,
        pages=pages)


@postb.route('/<alias>')
def view(alias=None):
    post = Post.query.filter(Post.alias == alias).filter(
        Post.status > 0).first_or_404()
    pages = Post.query.filter_by(status=3).order_by(Post.id).all()
    return render_template('post.html', post=post, pages=pages)


@postb.route('/robots.txt')
def robots():
    return '''
User-agent: *
Crawl-delay: 2
Disallow: /tag/*
Host: gunlinux.org
'''


@postb.route('/rss.xml')
def rss():
    date = datetime.datetime.now()
    list_posts = Post.query.filter(Post.status == 1).order_by(
        Post.publishedon.desc()).all()
    return render_template('rss.xml', posts=list_posts, date=date)
