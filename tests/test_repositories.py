"""Unit tests for the repository layer."""

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
from blog.repos.post import PostRepository
from blog.repos.category import CategoryRepository
from blog.repos.tag import TagRepository
from blog.repos.user import UserRepository
from blog.repos.icon import IconRepository
from blog.post.models import Post as PostORM
from blog.category.models import Category as CategoryORM
from blog.tags.models import Tag as TagORM
from blog.user.models import User as UserORM
from blog.post.models import Icon as IconORM


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
def post_repository(app):
    """Create a PostRepository instance for testing."""
    with app.app_context():
        return PostRepository(db.session)


@pytest.fixture()
def category_repository(app):
    """Create a CategoryRepository instance for testing."""
    with app.app_context():
        return CategoryRepository(db.session)


@pytest.fixture()
def tag_repository(app):
    """Create a TagRepository instance for testing."""
    with app.app_context():
        return TagRepository(db.session)


@pytest.fixture()
def user_repository(app):
    """Create a UserRepository instance for testing."""
    with app.app_context():
        return UserRepository(db.session)


@pytest.fixture()
def icon_repository(app):
    """Create an IconRepository instance for testing."""
    with app.app_context():
        return IconRepository(db.session)


class TestPostRepository:
    """Test cases for PostRepository."""

    def test_create_post(self, app, post_repository):
        """Test creating a new post."""
        with app.app_context():
            # Create a post domain model
            post_domain = PostDomain(
                pagetitle="Test Post",
                alias="test-post",
                content="This is a test post",
                createdon=datetime.datetime.now(datetime.timezone.utc),
                publishedon=datetime.datetime.now(datetime.timezone.utc),
            )

            # Create the post using the repository
            created_post = post_repository.create(post_domain)

            # Verify the post was created
            assert created_post.id is not None
            assert created_post.pagetitle == "Test Post"
            assert created_post.alias == "test-post"

            # Verify the ORM model was created
            stmt = db.select(PostORM).where(PostORM.id == created_post.id)
            post_orm = db.session.scalar(stmt)
            assert post_orm is not None
            assert post_orm.pagetitle == "Test Post"
            assert post_orm.alias == "test-post"

    def test_get_by_id(self, app, post_repository):
        """Test getting a post by ID."""
        with app.app_context():
            # Create a post first
            post_domain = PostDomain(
                pagetitle="Test Post",
                alias="test-post",
                content="This is a test post",
                createdon=datetime.datetime.now(datetime.timezone.utc),
                publishedon=datetime.datetime.now(datetime.timezone.utc),
            )
            created_post = post_repository.create(post_domain)

            # Get the post by ID
            retrieved_post = post_repository.get_by_id(created_post.id)

            # Verify the post was retrieved
            assert retrieved_post is not None
            assert retrieved_post.id == created_post.id
            assert retrieved_post.pagetitle == "Test Post"

            # Verify it's a domain model, not an ORM model
            assert isinstance(retrieved_post, PostDomain)
            assert not hasattr(retrieved_post, "_sa_instance_state")

    def test_to_domain_model_mapping(self, app, post_repository):
        """Test that _to_domain_model correctly maps ORM to domain model."""
        with app.app_context():
            # Create an ORM model directly
            post_orm = PostORM()
            post_orm.pagetitle = "Test Post"
            post_orm.alias = "test-post"
            post_orm.content = "This is a test post"
            post_orm.createdon = datetime.datetime.now(datetime.timezone.utc)
            post_orm.publishedon = datetime.datetime.now(datetime.timezone.utc)
            db.session.add(post_orm)
            db.session.flush()

            # Convert to domain model
            domain_model = post_repository._to_domain_model(post_orm)

            # Verify the mapping is correct
            assert isinstance(domain_model, PostDomain)
            assert domain_model.id == post_orm.id
            assert domain_model.pagetitle == post_orm.pagetitle
            assert domain_model.alias == post_orm.alias
            assert domain_model.content == post_orm.content
            assert domain_model.createdon == post_orm.createdon
            assert domain_model.publishedon == post_orm.publishedon
            assert domain_model.category_id == post_orm.category_id
            assert domain_model.user_id == post_orm.user_id

    def test_domain_to_orm_mapping(self, app, post_repository):
        """Test that domain model properties correctly map to ORM model."""
        with app.app_context():
            # Create a domain model
            post_domain = PostDomain(
                id=1,
                pagetitle="Test Post",
                alias="test-post",
                content="This is a test post",
                createdon=datetime.datetime.now(datetime.timezone.utc),
                publishedon=datetime.datetime.now(datetime.timezone.utc),
                category_id=1,
                user_id=1,
            )

            # Create an ORM model and map properties
            post_orm = PostORM()
            post_orm.pagetitle = post_domain.pagetitle
            post_orm.alias = post_domain.alias
            post_orm.content = post_domain.content
            post_orm.createdon = post_domain.createdon
            post_orm.publishedon = post_domain.publishedon
            post_orm.category_id = post_domain.category_id
            post_orm.user_id = post_domain.user_id

            # Verify the mapping is correct
            assert post_orm.pagetitle == post_domain.pagetitle
            assert post_orm.alias == post_domain.alias
            assert post_orm.content == post_domain.content
            assert post_orm.createdon == post_domain.createdon
            assert post_orm.publishedon == post_domain.publishedon
            assert post_orm.category_id == post_domain.category_id
            assert post_orm.user_id == post_domain.user_id


class TestCategoryRepository:
    """Test cases for CategoryRepository."""

    def test_create_category(self, app, category_repository):
        """Test creating a new category."""
        with app.app_context():
            # Create a category domain model
            category_domain = CategoryDomain(
                title="Test Category", alias="test-category"
            )

            # Create the category using the repository
            created_category = category_repository.create(category_domain)

            # Verify the category was created
            assert created_category.id is not None
            assert created_category.title == "Test Category"
            assert created_category.alias == "test-category"

            # Verify the ORM model was created
            stmt = db.select(CategoryORM).where(CategoryORM.id == created_category.id)
            category_orm = db.session.scalar(stmt)
            assert category_orm is not None
            assert category_orm.title == "Test Category"
            assert category_orm.alias == "test-category"

    def test_get_by_id(self, app, category_repository):
        """Test getting a category by ID."""
        with app.app_context():
            # Create a category first
            category_domain = CategoryDomain(
                title="Test Category", alias="test-category"
            )
            created_category = category_repository.create(category_domain)

            # Get the category by ID
            retrieved_category = category_repository.get_by_id(created_category.id)

            # Verify the category was retrieved correctly
            assert retrieved_category is not None
            assert retrieved_category.id == created_category.id
            assert retrieved_category.title == "Test Category"

            # Verify it's a domain model, not an ORM model
            assert isinstance(retrieved_category, CategoryDomain)
            assert not hasattr(retrieved_category, "_sa_instance_state")

    def test_to_domain_model_mapping(self, app, category_repository):
        """Test that _to_domain_model correctly maps ORM to domain model."""
        with app.app_context():
            # Create an ORM model directly
            category_orm = CategoryORM()
            category_orm.title = "Test Category"
            category_orm.alias = "test-category"
            category_orm.template = "test-template"
            db.session.add(category_orm)
            db.session.flush()

            # Convert to domain model
            domain_model = category_repository._to_domain_model(category_orm)

            # Verify the mapping is correct
            assert isinstance(domain_model, CategoryDomain)
            assert domain_model.id == category_orm.id
            assert domain_model.title == category_orm.title
            assert domain_model.alias == category_orm.alias
            assert domain_model.template == category_orm.template

    def test_domain_to_orm_mapping(self, app, category_repository):
        """Test that domain model properties correctly map to ORM model."""
        with app.app_context():
            # Create a domain model
            category_domain = CategoryDomain(
                id=1,
                title="Test Category",
                alias="test-category",
                template="test-template",
            )

            # Create an ORM model and map properties
            category_orm = CategoryORM()
            category_orm.title = category_domain.title
            category_orm.alias = category_domain.alias
            category_orm.template = category_domain.template

            # Verify the mapping is correct
            assert category_orm.title == category_domain.title
            assert category_orm.alias == category_domain.alias
            assert category_orm.template == category_domain.template


class TestTagRepository:
    """Test cases for TagRepository."""

    def test_create_tag(self, app, tag_repository):
        """Test creating a new tag."""
        with app.app_context():
            # Create a tag domain model
            tag_domain = TagDomain(title="Test Tag", alias="test-tag")

            # Create the tag using the repository
            created_tag = tag_repository.create(tag_domain)

            # Verify the tag was created
            assert created_tag.id is not None
            assert created_tag.title == "Test Tag"
            assert created_tag.alias == "test-tag"

            # Verify the ORM model was created
            stmt = db.select(TagORM).where(TagORM.id == created_tag.id)
            tag_orm = db.session.scalar(stmt)
            assert tag_orm is not None
            assert tag_orm.title == "Test Tag"
            assert tag_orm.alias == "test-tag"

    def test_get_by_id(self, app, tag_repository):
        """Test getting a tag by ID."""
        with app.app_context():
            # Create a tag first
            tag_domain = TagDomain(title="Test Tag", alias="test-tag")
            created_tag = tag_repository.create(tag_domain)

            # Get the tag by ID
            retrieved_tag = tag_repository.get_by_id(created_tag.id)

            # Verify the tag was retrieved correctly
            assert retrieved_tag is not None
            assert retrieved_tag.id == created_tag.id
            assert retrieved_tag.title == "Test Tag"

            # Verify it's a domain model, not an ORM model
            assert isinstance(retrieved_tag, TagDomain)
            assert not hasattr(retrieved_tag, "_sa_instance_state")

    def test_to_domain_model_mapping(self, app, tag_repository):
        """Test that _to_domain_model correctly maps ORM to domain model."""
        with app.app_context():
            # Create an ORM model directly
            tag_orm = TagORM()
            tag_orm.title = "Test Tag"
            tag_orm.alias = "test-tag"
            db.session.add(tag_orm)
            db.session.flush()

            # Convert to domain model
            domain_model = tag_repository._to_domain_model(tag_orm)

            # Verify the mapping is correct
            assert isinstance(domain_model, TagDomain)
            assert domain_model.id == tag_orm.id
            assert domain_model.title == tag_orm.title
            assert domain_model.alias == tag_orm.alias

    def test_domain_to_orm_mapping(self, app, tag_repository):
        """Test that domain model properties correctly map to ORM model."""
        with app.app_context():
            # Create a domain model
            tag_domain = TagDomain(
                id=1,
                title="Test Tag",
                alias="test-tag",
            )

            # Create an ORM model and map properties
            tag_orm = TagORM()
            tag_orm.title = tag_domain.title
            tag_orm.alias = tag_domain.alias

            # Verify the mapping is correct
            assert tag_orm.title == tag_domain.title
            assert tag_orm.alias == tag_domain.alias


class TestUserRepository:
    """Test cases for UserRepository."""

    def test_create_user(self, app, user_repository):
        """Test creating a new user."""
        with app.app_context():
            # Create a user domain model
            user_domain = UserDomain(name="testuser", password="testpassword")

            # Create the user using the repository
            created_user = user_repository.create(user_domain)

            # Verify the user was created
            assert created_user.id is not None
            assert created_user.name == "testuser"

            # Verify the ORM model was created
            stmt = db.select(UserORM).where(UserORM.id == created_user.id)
            user_orm = db.session.scalar(stmt)
            assert user_orm is not None
            assert user_orm.name == "testuser"

    def test_get_by_id(self, app, user_repository):
        """Test getting a user by ID."""
        with app.app_context():
            # Create a user first
            user_domain = UserDomain(name="testuser", password="testpassword")
            created_user = user_repository.create(user_domain)

            # Get the user by ID
            retrieved_user = user_repository.get_by_id(created_user.id)

            # Verify the user was retrieved correctly
            assert retrieved_user is not None
            assert retrieved_user.id == created_user.id
            assert retrieved_user.name == "testuser"

            # Verify it's a domain model, not an ORM model
            assert isinstance(retrieved_user, UserDomain)
            assert not hasattr(retrieved_user, "_sa_instance_state")

    def test_to_domain_model_mapping(self, app, user_repository):
        """Test that _to_domain_model correctly maps ORM to domain model."""
        with app.app_context():
            # Create an ORM model directly
            user_orm = UserORM()
            user_orm.name = "testuser"
            user_orm.password = "testpassword"
            user_orm.authenticated = 1
            user_orm.createdon = datetime.datetime.now(datetime.timezone.utc)
            db.session.add(user_orm)
            db.session.flush()

            # Convert to domain model
            domain_model = user_repository._to_domain_model(user_orm)

            # Verify the mapping is correct
            assert isinstance(domain_model, UserDomain)
            assert domain_model.id == user_orm.id
            assert domain_model.name == user_orm.name
            assert domain_model.password == user_orm.password
            assert domain_model.authenticated == bool(user_orm.authenticated)
            assert domain_model.createdon == user_orm.createdon

    def test_domain_to_orm_mapping(self, app, user_repository):
        """Test that domain model properties correctly map to ORM model."""
        with app.app_context():
            # Create a domain model
            user_domain = UserDomain(
                id=1,
                name="testuser",
                password="testpassword",
                authenticated=True,
                createdon=datetime.datetime.now(datetime.timezone.utc),
            )

            # Create an ORM model and map properties
            user_orm = UserORM()
            user_orm.name = user_domain.name
            user_orm.password = user_domain.password
            user_orm.authenticated = (
                int(user_domain.authenticated)
                if user_domain.authenticated is not None
                else 0
            )
            user_orm.createdon = user_domain.createdon

            # Verify the mapping is correct
            assert user_orm.name == user_domain.name
            assert user_orm.password == user_domain.password
            assert (
                user_orm.authenticated == int(user_domain.authenticated)
                if user_domain.authenticated is not None
                else 0
            )
            assert user_orm.createdon == user_domain.createdon


class TestIconRepository:
    """Test cases for IconRepository."""

    def test_create_icon(self, app, icon_repository):
        """Test creating a new icon."""
        with app.app_context():
            # Create an icon domain model
            icon_domain = IconDomain(
                title="Test Icon",
                url="http://example.com/icon.png",
                content="Icon content",
            )

            # Create the icon using the repository
            created_icon = icon_repository.create(icon_domain)

            # Verify the icon was created
            assert created_icon.id is not None
            assert created_icon.title == "Test Icon"
            assert created_icon.url == "http://example.com/icon.png"

            # Verify the ORM model was created
            stmt = db.select(IconORM).where(IconORM.id == created_icon.id)
            icon_orm = db.session.scalar(stmt)
            assert icon_orm is not None
            assert icon_orm.title == "Test Icon"
            assert icon_orm.url == "http://example.com/icon.png"

    def test_get_by_id(self, app, icon_repository):
        """Test getting an icon by ID."""
        with app.app_context():
            # Create an icon first
            icon_domain = IconDomain(
                title="Test Icon",
                url="http://example.com/icon.png",
                content="Icon content",
            )
            created_icon = icon_repository.create(icon_domain)

            # Get the icon by ID
            retrieved_icon = icon_repository.get_by_id(created_icon.id)

            # Verify the icon was retrieved correctly
            assert retrieved_icon is not None
            assert retrieved_icon.id == created_icon.id
            assert retrieved_icon.title == "Test Icon"

            # Verify it's a domain model, not an ORM model
            assert isinstance(retrieved_icon, IconDomain)
            assert not hasattr(retrieved_icon, "_sa_instance_state")

    def test_to_domain_model_mapping(self, app, icon_repository):
        """Test that _to_domain_model correctly maps ORM to domain model."""
        with app.app_context():
            # Create an ORM model directly
            icon_orm = IconORM()
            icon_orm.title = "Test Icon"
            icon_orm.url = "http://example.com/icon.png"
            icon_orm.content = "Icon content"
            db.session.add(icon_orm)
            db.session.flush()

            # Convert to domain model
            domain_model = icon_repository._to_domain_model(icon_orm)

            # Verify the mapping is correct
            assert isinstance(domain_model, IconDomain)
            assert domain_model.id == icon_orm.id
            assert domain_model.title == icon_orm.title
            assert domain_model.url == icon_orm.url
            assert domain_model.content == icon_orm.content

    def test_domain_to_orm_mapping(self, app, icon_repository):
        """Test that domain model properties correctly map to ORM model."""
        with app.app_context():
            # Create a domain model
            icon_domain = IconDomain(
                id=1,
                title="Test Icon",
                url="http://example.com/icon.png",
                content="Icon content",
            )

            # Create an ORM model and map properties
            icon_orm = IconORM()
            icon_orm.title = icon_domain.title
            icon_orm.url = icon_domain.url
            icon_orm.content = icon_domain.content

            # Verify the mapping is correct
            assert icon_orm.title == icon_domain.title
            assert icon_orm.url == icon_domain.url
            assert icon_orm.content == icon_domain.content
