import os

from flask_admin.contrib import fileadmin, sqla
from blog.extensions import db
from blog.post.models import Post
from blog.category.models import Category
from blog.tags.models import Tag
from blog.user.models import User


class UserView(sqla.ModelView):
    column_exclude_list = ['content', 'alias']
    create_template = 'admin/create.html'
    edit_template = 'admin/edit.html'

    column_default_sort = ('id', True)


class PostView(UserView):
    column_hide_backrefs = False
    column_list = ('pagetitle', 'puslishedon', 'tags',)


def create_admin(config_admin):
    config_admin.add_view(PostView(Post, db.session, endpoint=''))
    config_admin.add_view(UserView(Category, db.session, endpoint=''))
    config_admin.add_view(UserView(Tag, db.session, endpoint=''))
    config_admin.add_view(UserView(User, db.session, endpoint=''))
    path = os.path.join(os.path.dirname(__file__), '../static/upload')
    config_admin.add_view(
        fileadmin.FileAdmin(
            path, '/static/upload',
            name='files'
        )
    )
