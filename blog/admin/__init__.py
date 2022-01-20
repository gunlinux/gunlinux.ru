# -*- coding: utf-8 -*-
import os

from flask_admin.contrib import fileadmin, sqla
from blog.extensions import db
from blog.models.post import Post, POST_STATUSES
from wtforms.fields import SelectField


def _status(view, _, model, name):
    view, name = name, view
    return POST_STATUSES.get(model.status, None)


class UserView(sqla.ModelView):
    form_excluded_columns = ['children', ]
    column_exclude_list = ['content', 'alias']
    create_template = 'admin/create.html'
    edit_template = 'admin/edit.html'

    form_overrides = dict(status=SelectField)
    form_args = dict(
        status=dict(choices=POST_STATUSES.items()),
    )
    column_formatters = {
        'status': _status
    }
    column_default_sort = ('id', True)


def create_admin(config_admin):
    config_admin.add_view(UserView(Post, db.session, endpoint=''))
    path = os.path.join(os.path.dirname(__file__), '../static/upload')
    config_admin.add_view(
        fileadmin.FileAdmin(
            path, '/static/upload',
            name='files'
        )
    )
