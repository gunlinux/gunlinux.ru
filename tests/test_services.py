"""Unit tests for the service layer."""

import pytest
import os
import datetime

from blog import create_app
from blog.extensions import db
from blog.domain.post import Post as PostDomain
from blog.domain.category import Category as CategoryDomain
from blog.domain.tag import Tag as TagDomain
from blog.domain.user import User as UserDomain
from blog.domain.icon import Icon as IconDomain
from blog.services.post import PostService, PostServiceError
from blog.services.category import CategoryService
from blog.services.tag import TagService
from blog.services.user import UserService
from blog.services.icon import IconService
from blog.repos.post import PostRepository
from blog.repos.category import CategoryRepository
from blog.repos.tag import TagRepository
from blog.repos.user import UserRepository
from blog.repos.icon import IconRepository


@pytest.fixture()
def app():
    os.environ["FLASK_ENV"] = "testing"
    app = create_app()
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def post_service(app):
    """Create a PostService instance for testing."""
    with app.app_context():
        repository = PostRepository(db.session)
        return PostService(repository)


@pytest.fixture()
def category_service(app):
    """Create a CategoryService instance for testing."""
    with app.app_context():
        repository = CategoryRepository(db.session)
        return CategoryService(repository)


@pytest.fixture()
def tag_service(app):
    """Create a TagService instance for testing."""
    with app.app_context():
        repository = TagRepository(db.session)
        return TagService(repository)


@pytest.fixture()
def user_service(app):
    """Create a UserService instance for testing."""
    with app.app_context():
        repository = UserRepository(db.session)
        return UserService(repository)


@pytest.fixture()
def icon_service(app):
    """Create an IconService instance for testing."""
    with app.app_context():
        repository = IconRepository(db.session)
        return IconService(repository)


class TestPostService:
    """Test cases for PostService."""

    def test_create_post(self, app, post_service):
        """Test creating a new post."""
        # Create a post domain model
        post_domain = PostDomain(
            pagetitle="Test Post",
            alias="test-post",
            content="This is a test post",
            createdon=datetime.datetime.now(datetime.timezone.utc),
            publishedon=datetime.datetime.now(datetime.timezone.utc),
        )

        # Create the post using the service
        created_post = post_service.create_post(post_domain)

        # Verify the post was created
        assert created_post.id is not None
        assert created_post.pagetitle == "Test Post"
        assert created_post.alias == "test-post"

    def test_service_returns_domain_models_not_orm_models(self, app, post_service):
        """Test that service layer methods return domain models, not ORM models."""
        # Create a post first
        post_domain = PostDomain(
            pagetitle="Test Post",
            alias="test-post",
            content="This is a test post",
            createdon=datetime.datetime.now(datetime.timezone.utc),
            publishedon=datetime.datetime.now(datetime.timezone.utc),
        )
        created_post = post_service.create_post(post_domain)

        # Verify all service methods return domain models
        # 1. get_post_by_id should return a domain model
        retrieved_post = post_service.get_post_by_id(created_post.id)
        assert isinstance(retrieved_post, PostDomain)
        assert not hasattr(
            retrieved_post, "_sa_instance_state"
        )  # ORM models have this attribute

        # 2. get_post_by_alias should return a domain model
        retrieved_post = post_service.get_post_by_alias("test-post")
        assert isinstance(retrieved_post, PostDomain)
        assert not hasattr(retrieved_post, "_sa_instance_state")

        # 3. get_all_posts should return domain models
        posts = post_service.get_all_posts()
        assert all(isinstance(post, PostDomain) for post in posts)
        assert all(not hasattr(post, "_sa_instance_state") for post in posts)

        # 4. get_published_posts should return domain models
        published_posts = post_service.get_published_posts()
        assert all(isinstance(post, PostDomain) for post in published_posts)
        assert all(not hasattr(post, "_sa_instance_state") for post in published_posts)

    def test_get_post_by_id(self, app, post_service):
        """Test getting a post by ID."""
        # Create a post first
        post_domain = PostDomain(
            pagetitle="Test Post",
            alias="test-post",
            content="This is a test post",
            createdon=datetime.datetime.now(datetime.timezone.utc),
            publishedon=datetime.datetime.now(datetime.timezone.utc),
        )

        created_post = post_service.create_post(post_domain)

        # Get the post by ID
        retrieved_post = post_service.get_post_by_id(created_post.id)

        # Verify the post was retrieved
        assert retrieved_post is not None
        assert retrieved_post.id == created_post.id
        assert retrieved_post.pagetitle == "Test Post"

    def test_update_post(self, app, post_service):
        """Test updating a post."""
        # Create a post first
        post_domain = PostDomain(
            pagetitle="Test Post",
            alias="test-post",
            content="This is a test post",
            createdon=datetime.datetime.now(datetime.timezone.utc),
            publishedon=datetime.datetime.now(datetime.timezone.utc),
        )
        created_post = post_service.create_post(post_domain)

        # Update the post
        created_post.pagetitle = "Updated Post"
        updated_post = post_service.update_post(created_post)

        # Verify the post was updated
        assert updated_post.pagetitle == "Updated Post"

    def test_update_nonexistent_post_raises_error(self, app, post_service):
        """Test that updating a nonexistent post raises an error."""
        # Try to update a post that doesn't exist
        post_domain = PostDomain(
            id=99999,  # Nonexistent ID
            pagetitle="Test Post",
            alias="test-post",
            content="This is a test post",
        )

        # Verify that updating a nonexistent post raises an error
        with pytest.raises(PostServiceError):
            post_service.update_post(post_domain)

    def test_delete_post(self, app, post_service):
        """Test deleting a post."""
        # Create a post first
        post_domain = PostDomain(
            pagetitle="Test Post",
            alias="test-post",
            content="This is a test post",
            createdon=datetime.datetime.now(datetime.timezone.utc),
            publishedon=datetime.datetime.now(datetime.timezone.utc),
        )
        created_post = post_service.create_post(post_domain)

        # Delete the post
        result = post_service.delete_post(created_post.id)

        # Verify the post was deleted
        assert result is True

        # Verify the post no longer exists
        retrieved_post = post_service.get_post_by_id(created_post.id)
        assert retrieved_post is None

    def test_delete_nonexistent_post(self, app, post_service):
        """Test deleting a nonexistent post."""
        # Try to delete a post that doesn't exist
        result = post_service.delete_post(99999)  # Nonexistent ID

        # Verify the result is False
        assert result is False

    def test_get_post_by_alias(self, app, post_service):
        """Test getting a post by alias."""
        # Create a post first
        post_domain = PostDomain(
            pagetitle="Test Post",
            alias="test-post",
            content="This is a test post",
            createdon=datetime.datetime.now(datetime.timezone.utc),
            publishedon=datetime.datetime.now(datetime.timezone.utc),
        )
        created_post = post_service.create_post(post_domain)

        # Get the post by alias
        retrieved_post = post_service.get_post_by_alias("test-post")

        # Verify the post was retrieved
        assert retrieved_post is not None
        assert retrieved_post.id == created_post.id
        assert retrieved_post.alias == "test-post"

    def test_get_all_posts(self, app, post_service):
        """Test getting all posts."""
        # Create a few posts
        post1_domain = PostDomain(
            pagetitle="Test Post 1",
            alias="test-post-1",
            content="This is test post 1",
            createdon=datetime.datetime.now(datetime.timezone.utc),
            publishedon=datetime.datetime.now(datetime.timezone.utc),
        )
        post_service.create_post(post1_domain)

        post2_domain = PostDomain(
            pagetitle="Test Post 2",
            alias="test-post-2",
            content="This is test post 2",
            createdon=datetime.datetime.now(datetime.timezone.utc),
            publishedon=datetime.datetime.now(datetime.timezone.utc),
        )
        post_service.create_post(post2_domain)

        # Get all posts
        posts = post_service.get_all_posts()

        # Verify we got the posts
        assert len(posts) >= 2
        aliases = [post.alias for post in posts]
        assert "test-post-1" in aliases
        assert "test-post-2" in aliases

    def test_get_published_posts(self, app, post_service):
        """Test getting published posts."""
        # Create a published post
        published_post_domain = PostDomain(
            pagetitle="Published Post",
            alias="published-post",
            content="This is a published post",
            createdon=datetime.datetime.now(datetime.timezone.utc),
            publishedon=datetime.datetime.now(datetime.timezone.utc),
        )
        post_service.create_post(published_post_domain)

        # Create an unpublished post
        unpublished_post_domain = PostDomain(
            pagetitle="Unpublished Post",
            alias="unpublished-post",
            content="This is an unpublished post",
            createdon=datetime.datetime.now(datetime.timezone.utc),
            # No publishedon field, so it's unpublished
        )
        post_service.create_post(unpublished_post_domain)

        # Get published posts
        published_posts = post_service.get_published_posts()

        # Verify we only got the published post
        assert len(published_posts) >= 1
        aliases = [post.alias for post in published_posts]
        assert "published-post" in aliases
        assert "unpublished-post" not in aliases


class TestCategoryService:
    """Test cases for CategoryService."""

    def test_create_category(self, app, category_service):
        """Test creating a new category."""
        with app.app_context():
            # Create a category domain model
            category_domain = CategoryDomain(
                title="Test Category", alias="test-category"
            )

            # Create the category using the service
            created_category = category_service.create_category(category_domain)

            # Verify the category was created
            assert created_category.id is not None
            assert created_category.title == "Test Category"
            assert created_category.alias == "test-category"

    def test_get_category_by_id(self, app, category_service):
        """Test getting a category by ID."""
        with app.app_context():
            # Create a category first
            category_domain = CategoryDomain(
                title="Test Category", alias="test-category"
            )
            created_category = category_service.create_category(category_domain)

            # Get the category by ID
            retrieved_category = category_service.get_category_by_id(
                created_category.id
            )

            # Verify the category was retrieved correctly
            assert retrieved_category is not None
            assert retrieved_category.id == created_category.id
            assert retrieved_category.title == "Test Category"

    def test_service_returns_domain_models_not_orm_models(self, app, category_service):
        """Test that service layer methods return domain models, not ORM models."""
        with app.app_context():
            # Create a category first
            category_domain = CategoryDomain(
                title="Test Category", alias="test-category"
            )
            created_category = category_service.create_category(category_domain)

            # Verify all service methods return domain models
            # get_category_by_id should return a domain model
            retrieved_category = category_service.get_category_by_id(
                created_category.id
            )
            assert isinstance(retrieved_category, CategoryDomain)
            assert not hasattr(
                retrieved_category, "_sa_instance_state"
            )  # ORM models have this attribute


class TestTagService:
    """Test cases for TagService."""

    def test_create_tag(self, app, tag_service):
        """Test creating a new tag."""
        with app.app_context():
            # Create a tag domain model
            tag_domain = TagDomain(title="Test Tag", alias="test-tag")

            # Create the tag using the service
            created_tag = tag_service.create_tag(tag_domain)

            # Verify the tag was created
            assert created_tag.id is not None
            assert created_tag.title == "Test Tag"
            assert created_tag.alias == "test-tag"

    def test_service_returns_domain_models_not_orm_models(self, app, tag_service):
        """Test that service layer methods return domain models, not ORM models."""
        with app.app_context():
            # Create a tag first
            tag_domain = TagDomain(title="Test Tag", alias="test-tag")
            created_tag = tag_service.create_tag(tag_domain)

            # Verify all service methods return domain models
            # get_tag_by_id should return a domain model
            # Tags don't have a get_by_id method in the current implementation
            # But we can verify that the created tag is a domain model
            assert isinstance(created_tag, TagDomain)
            assert not hasattr(
                created_tag, "_sa_instance_state"
            )  # ORM models have this attribute


class TestUserService:
    """Test cases for UserService."""

    def test_create_user(self, app, user_service):
        """Test creating a new user."""
        with app.app_context():
            # Create a user domain model
            user_domain = UserDomain(name="testuser", password="testpassword")

            # Create the user using the service
            created_user = user_service.create_user(user_domain)

            # Verify the user was created
            assert created_user.id is not None
            assert created_user.name == "testuser"

    def test_authenticate_user(self, app, user_service):
        """Test authenticating a user."""
        with app.app_context():
            # Create a user first
            user_domain = UserDomain(name="testuser", password="testpassword")
            created_user = user_service.create_user(user_domain)
            # Set the password properly (this would normally be done in the repo)
            from blog.user.models import User as UserORM

            user_orm = db.session.get(UserORM, created_user.id)
            if user_orm:
                user_orm.set_password("testpassword")
                db.session.commit()

            # Authenticate the user
            authenticated_user = user_service.authenticate_user(
                "testuser", "testpassword"
            )

            # Verify the user was authenticated
            assert authenticated_user is not None
            assert authenticated_user.name == "testuser"

    def test_service_returns_domain_models_not_orm_models(self, app, user_service):
        """Test that service layer methods return domain models, not ORM models."""
        with app.app_context():
            # Create a user first
            user_domain = UserDomain(name="testuser", password="testpassword")
            created_user = user_service.create_user(user_domain)

            # Verify all service methods return domain models
            # get_user_by_id should return a domain model
            # Users don't have a get_by_id method in the current implementation
            # But we can verify that the created user is a domain model
            assert isinstance(created_user, UserDomain)
            assert not hasattr(
                created_user, "_sa_instance_state"
            )  # ORM models have this attribute


class TestIconService:
    """Test cases for IconService."""

    def test_create_icon(self, app, icon_service):
        """Test creating a new icon."""
        with app.app_context():
            # Create an icon domain model
            icon_domain = IconDomain(
                title="Test Icon",
                url="http://example.com/icon.png",
                content="Icon content",
            )

            # Create the icon using the service
            created_icon = icon_service.create_icon(icon_domain)

            # Verify the icon was created
            assert created_icon.id is not None
            assert created_icon.title == "Test Icon"
            assert created_icon.url == "http://example.com/icon.png"

    def test_service_returns_domain_models_not_orm_models(self, app, icon_service):
        """Test that service layer methods return domain models, not ORM models."""
        with app.app_context():
            # Create an icon first
            icon_domain = IconDomain(
                title="Test Icon",
                url="http://example.com/icon.png",
                content="Icon content",
            )
            created_icon = icon_service.create_icon(icon_domain)

            # Verify all service methods return domain models
            # get_icon_by_id should return a domain model
            # Icons don't have a get_by_id method in the current implementation
            # But we can verify that the created icon is a domain model
            assert isinstance(created_icon, IconDomain)
            assert not hasattr(
                created_icon, "_sa_instance_state"
            )  # ORM models have this attribute
