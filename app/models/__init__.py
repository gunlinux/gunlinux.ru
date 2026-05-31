# Import all models so they are registered with Base.metadata
from app.models.category import Category as Category  # noqa: F401
from app.models.post import Icon as Icon  # noqa: F401
from app.models.post import Post as Post
from app.models.tag import Tag as Tag  # noqa: F401
from app.models.user import User as User  # noqa: F401
