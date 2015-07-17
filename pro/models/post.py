# -*- coding: utf-8 -*-
""" SqlAlchemy models """
from pro.extensions import db
import datetime


class Post(db.Model):
    STATUS = {
        '0': u'Черновик',
        '1': u'Опубликован',
        '2': u'Архив',
        '3': u'Страница'
    }
    ''' orm model for blog post'''
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    pagetitle = db.Column(db.String(255), default='')
    alias = db.Column(db.String(255), default='')
    content = db.Column(db.Text)
    createdon = db.Column(db.DateTime, default=datetime.datetime.now)
    publishedon = db.Column(db.DateTime, default=datetime.datetime.now)
    status = db.Column(db.Integer, default=0)

    def __repr__(self):
        return '<Post {0}>'.format(self.alias)

    def __unicode__(self):
        return '<Post {0}>'.format(self.pagetitle)
