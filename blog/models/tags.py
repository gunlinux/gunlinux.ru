from blog.extensions import db
from sqlalchemy.ext.declarative import declarative_base

class Posts_Tags(db.Model):
    __tablename__ = 'posts_tags'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'))


class Tag(db.Model):
    """orm model for blog post."""

    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), default='', unique=True)
    posts = db.relationship("Post", secondary="posts_tags", back_populates="tags")

    def __init__(self, title):
        self.title = title

    def __str__(self):
        return f'{self.title}'