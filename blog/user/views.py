from flask import render_template, Blueprint, current_app
import sqlalchemy as sa
from blog import db
from blog.user.models import User 
from blog.post.models import Post 


user_blueprint = Blueprint("userb", __name__)


@user_blueprint.route('/')
def user_list():
    page_category = current_app.config['PAGE_CATEGORY']
    pages_query = sa.select(Post).where(Post.category_id == page_category)
    pages = db.session.scalars(pages_query).all()
    users = []

    return render_template("users.html", users=users, pages=pages)


@user_blueprint.route('/<alias>')
def user_view(alias=None):
    page_category = current_app.config['PAGE_CATEGORY']
    pages_query = sa.select(Post).where(Post.category_id == page_category)
    pages = db.session.scalars(pages_query).all()
    user = 'loki'

    return render_template('post.html', user=user, pages=pages)

