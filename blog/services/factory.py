"""Service factory for creating service instances with proper dependency injection."""

from blog.extensions import db
from blog.repos.post import PostRepository
from blog.repos.category import CategoryRepository
from blog.repos.icon import IconRepository
from blog.repos.tag import TagRepository
from blog.repos.user import UserRepository
from blog.services.post import PostService
from blog.services.category import CategoryService
from blog.services.icon import IconService
from blog.services.tag import TagService
from blog.services.user import UserService
from blog.services.content_formatter import ContentFormatter


class ServiceFactory:
    """Factory for creating service instances with proper dependency injection."""

    @staticmethod
    def create_post_service():
        """Create a PostService instance with its dependencies."""
        post_repository = PostRepository(db.session)
        return PostService(post_repository)

    @staticmethod
    def create_category_service():
        """Create a CategoryService instance with its dependencies."""
        category_repository = CategoryRepository(db.session)
        return CategoryService(category_repository)

    @staticmethod
    def create_icon_service():
        """Create an IconService instance with its dependencies."""
        icon_repository = IconRepository(db.session)
        return IconService(icon_repository)

    @staticmethod
    def create_tag_service():
        """Create a TagService instance with its dependencies."""
        tag_repository = TagRepository(db.session)
        return TagService(tag_repository)

    @staticmethod
    def create_user_service():
        """Create a UserService instance with its dependencies."""
        user_repository = UserRepository(db.session)
        return UserService(user_repository)

    @staticmethod
    def create_formatter_service():
        """Create a UserService instance with its dependencies."""
        return ContentFormatter()
