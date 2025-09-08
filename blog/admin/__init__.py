import os

from flask_admin.contrib import fileadmin, sqla
from flask_login import current_user

from blog.category.models import Category
from blog.extensions import db
from blog.post.models import Post, Icon
from blog.tags.models import Tag
from blog.user.models import User


class UserView(sqla.ModelView):
    column_exclude_list = ["content", "alias"]
    create_template = "admin/create.html"
    edit_template = "admin/edit.html"

    column_default_sort = ("id", True)

    def is_accessible(self):
        return current_user.is_authenticated


class PostView(UserView):
    column_hide_backrefs = False
    column_list = (
        "pagetitle",
        "puslishedon",
        "tags",
    )


class MyFileAdmin(fileadmin.FileAdmin):
    def is_accessible(self):
        return current_user.is_authenticated


def create_admin(config_admin):
    config_admin.add_view(PostView(Post, db.session, endpoint="admin_post"))
    config_admin.add_view(UserView(Category, db.session, endpoint="admin_category"))
    config_admin.add_view(UserView(Tag, db.session, endpoint="admin_tag"))
    config_admin.add_view(UserView(User, db.session, endpoint="admin_user"))
    config_admin.add_view(UserView(Icon, db.session, endpoint="admin_icon"))
    path = os.path.join(os.path.dirname(__file__), "../static/upload")
    config_admin.add_view(MyFileAdmin(path, "/static/upload", name="files"))
