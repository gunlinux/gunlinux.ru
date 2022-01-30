"""SqlAlchemy models."""


from blog.extensions import db


class Category(db.Model):
    """orm model for blog post."""

    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), default='')
    alias = db.Column(db.String(255), unique=True, nullable=False)

    def __init__(self, title, alias):
        self.title = title
        self.alias = alias

    def __str__(self):
        return f'{self.title}'
