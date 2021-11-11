"""SqlAlchemy models."""

import datetime

from pro.extensions import db

TITLE_LEN = 255
URL_LEN = 255
POST_STATUSES = {
    0: 'Draft',
    1: 'Page',
    2: 'Archive',
    3: 'Special',
    4: 'Published',
}


class Post(db.Model):
    """orm model for blog post."""

    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    pagetitle = db.Column(db.String(TITLE_LEN), default='')
    alias = db.Column(db.String(TITLE_LEN), default='')
    content = db.Column(db.Text)
    createdon = db.Column(db.DateTime, default=datetime.datetime.now)
    publishedon = db.Column(db.DateTime, default=datetime.datetime.now)
    status = db.Column(db.Integer, default=0)
    bg = db.Column(db.String(URL_LEN), default='')
