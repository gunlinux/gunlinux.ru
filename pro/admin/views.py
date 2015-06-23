# -*- coding: utf-8 -*-
import os
'''
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.fileadmin import FileAdmin
'''
from flask_admin.contrib import sqla, fileadmin

from .. import flask_admin, db
from ..postb.models import Post
from wtforms.fields import SelectField


class UserView(sqla.ModelView):
    form_excluded_columns = ['children', ]
    column_exclude_list = ['content', 'alias']
    create_template = 'admin/create.html'
    edit_template = 'admin/edit.html'

    def _status(view, context, model, name):
        return Post.STATUS.get(str(model.status))

    form_overrides = dict(status=SelectField)
    form_args = dict(
        status=dict(choices=Post.STATUS.items()),
    )
    column_formatters = {
        'status': _status
    }
    column_default_sort = ('id', True)

flask_admin.add_view(UserView(Post, db.session))

path = os.path.join(os.path.dirname(__file__), '../static/upload')

flask_admin.add_view(
    fileadmin.FileAdmin(
        path, '/static/upload',
        name='files'
    )
)
