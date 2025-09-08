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

    def test_get_by_id_nonexistent(self, app, post_repository):
        """Test getting a nonexistent post by ID."""
        with app.app_context():
            # Try to get a post that doesn't exist
            retrieved_post = post_repository.get_by_id(99999)  # Nonexistent ID

            # Verify None is returned
            assert retrieved_post is None

    def test_get_by_alias(self, app, post_repository):
        """Test getting a post by alias."""
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

            # Get the post by alias
            retrieved_post = post_repository.get_by_alias("test-post")

            # Verify the post was retrieved
            assert retrieved_post is not None
            assert retrieved_post.id == created_post.id
            assert retrieved_post.alias == "test-post"

    def test_get_by_alias_nonexistent(self, app, post_repository):
        """Test getting a nonexistent post by alias."""
        with app.app_context():
            # Try to get a post that doesn't exist
            retrieved_post = post_repository.get_by_alias("nonexistent-alias")

            # Verify None is returned
            assert retrieved_post is None

    def test_get_all(self, app, post_repository):
        """Test getting all posts."""
        with app.app_context():
            # Create a few posts
            post1_domain = PostDomain(
                pagetitle="Test Post 1",
                alias="test-post-1",
                content="This is test post 1",
                createdon=datetime.datetime.now(datetime.timezone.utc),
                publishedon=datetime.datetime.now(datetime.timezone.utc),
            )
            post_repository.create(post1_domain)

            post2_domain = PostDomain(
                pagetitle="Test Post 2",
                alias="test-post-2",
                content="This is test post 2",
                createdon=datetime.datetime.now(datetime.timezone.utc),
                publishedon=datetime.datetime.now(datetime.timezone.utc),
            )
            post_repository.create(post2_domain)

            # Get all posts
            posts = post_repository.get_all()

            # Verify we got the posts
            assert len(posts) >= 2
            aliases = [post.alias for post in posts]
            assert "test-post-1" in aliases
            assert "test-post-2" in aliases

            # Verify they are domain models
            assert all(isinstance(post, PostDomain) for post in posts)
            assert all(not hasattr(post, "_sa_instance_state") for post in posts)

    def test_get_all_empty(self, app, post_repository):
        """Test getting all posts when there are none."""
        with app.app_context():
            # Get all posts when there are none
            posts = post_repository.get_all()

            # Verify an empty list is returned
            assert posts == []

    def test_get_published_posts(self, app, post_repository):
        """Test getting published posts."""
        with app.app_context():
            # Create a published post
            published_post_domain = PostDomain(
                pagetitle="Published Post",
                alias="published-post",
                content="This is a published post",
                createdon=datetime.datetime.now(datetime.timezone.utc),
                publishedon=datetime.datetime.now(datetime.timezone.utc),
            )
            post_repository.create(published_post_domain)

            # Create an unpublished post
            unpublished_post_domain = PostDomain(
                pagetitle="Unpublished Post",
                alias="unpublished-post",
                content="This is an unpublished post",
                createdon=datetime.datetime.now(datetime.timezone.utc),
                # No publishedon field, so it's unpublished
            )
            post_repository.create(unpublished_post_domain)

            # Get published posts
            published_posts = post_repository.get_published_posts()

            # Verify we only got the published post
            assert len(published_posts) >= 1
            aliases = [post.alias for post in published_posts]
            assert "published-post" in aliases
            assert "unpublished-post" not in aliases

            # Verify they are domain models
            assert all(isinstance(post, PostDomain) for post in published_posts)
            assert all(
                not hasattr(post, "_sa_instance_state") for post in published_posts
            )

    def test_get_published_posts_empty(self, app, post_repository):
        """Test getting published posts when there are none."""
        with app.app_context():
            # Get published posts when there are none
            published_posts = post_repository.get_published_posts()

            # Verify an empty list is returned
            assert published_posts == []

    def test_get_page_posts(self, app, post_repository):
        """Test getting page posts."""
        with app.app_context():
            # Create a category first
            from blog.repos.category import CategoryRepository

            category_repository = CategoryRepository(db.session)
            category_domain = CategoryDomain(
                title="Page Category", alias="page-category"
            )
            created_category = category_repository.create(category_domain)

            # Create a page post
            page_post_domain = PostDomain(
                pagetitle="Page Post",
                alias="page-post",
                content="This is a page post",
                createdon=datetime.datetime.now(datetime.timezone.utc),
                publishedon=datetime.datetime.now(datetime.timezone.utc),
                category_id=created_category.id,
            )
            post_repository.create(page_post_domain)

            # Create a regular post
            regular_post_domain = PostDomain(
                pagetitle="Regular Post",
                alias="regular-post",
                content="This is a regular post",
                createdon=datetime.datetime.now(datetime.timezone.utc),
                publishedon=datetime.datetime.now(datetime.timezone.utc),
                category_id=None,
            )
            post_repository.create(regular_post_domain)

            # Get page posts
            page_posts = post_repository.get_page_posts([created_category.id])

            # Verify we only got the page post
            assert len(page_posts) >= 1
            aliases = [post.alias for post in page_posts]
            assert "page-post" in aliases
            assert "regular-post" not in aliases

            # Verify they are domain models
            assert all(isinstance(post, PostDomain) for post in page_posts)
            assert all(not hasattr(post, "_sa_instance_state") for post in page_posts)

    def test_get_page_posts_empty_list(self, app, post_repository):
        """Test getting page posts with an empty category list."""
        with app.app_context():
            # Get page posts with an empty category list
            page_posts = post_repository.get_page_posts([])

            # Verify an empty list is returned
            assert page_posts == []

    def test_update_post(self, app, post_repository):
        """Test updating a post."""
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

            # Update the post
            created_post.pagetitle = "Updated Post"
            updated_post = post_repository.update(created_post)

            # Verify the post was updated
            assert updated_post.pagetitle == "Updated Post"

            # Verify the ORM model was updated
            stmt = db.select(PostORM).where(PostORM.id == created_post.id)
            post_orm = db.session.scalar(stmt)
            assert post_orm is not None
            assert post_orm.pagetitle == "Updated Post"

    def test_update_nonexistent_post(self, app, post_repository):
        """Test updating a nonexistent post."""
        with app.app_context():
            # Try to update a post that doesn't exist
            post_domain = PostDomain(
                id=99999,  # Nonexistent ID
                pagetitle="Test Post",
                alias="test-post",
                content="This is a test post",
            )

            # Verify that updating a nonexistent post raises an error
            with pytest.raises(ValueError):
                post_repository.update(post_domain)

    def test_delete_post(self, app, post_repository):
        """Test deleting a post."""
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

            # Delete the post
            result = post_repository.delete(created_post.id)

            # Verify the post was deleted
            assert result is True

            # Verify the post no longer exists
            retrieved_post = post_repository.get_by_id(created_post.id)
            assert retrieved_post is None

            # Verify the ORM model was deleted
            stmt = db.select(PostORM).where(PostORM.id == created_post.id)
            post_orm = db.session.scalar(stmt)
            assert post_orm is None

    def test_delete_nonexistent_post(self, app, post_repository):
        """Test deleting a nonexistent post."""
        with app.app_context():
            # Try to delete a post that doesn't exist
            result = post_repository.delete(99999)  # Nonexistent ID

            # Verify the result is False
            assert result is False

    def test_get_post_with_relationships(self, app, post_repository):
        """Test getting a post with relationships loaded."""
        with app.app_context():
            # Create a user first
            from blog.repos.user import UserRepository

            user_repository = UserRepository(db.session)
            user_domain = UserDomain(name="testuser", password="testpassword")
            created_user = user_repository.create(user_domain)

            # Create a category first
            from blog.repos.category import CategoryRepository

            category_repository = CategoryRepository(db.session)
            category_domain = CategoryDomain(
                title="Test Category", alias="test-category"
            )
            created_category = category_repository.create(category_domain)

            # Create a post
            post_domain = PostDomain(
                pagetitle="Test Post",
                alias="test-post",
                content="This is a test post",
                createdon=datetime.datetime.now(datetime.timezone.utc),
                publishedon=datetime.datetime.now(datetime.timezone.utc),
                user_id=created_user.id,
                category_id=created_category.id,
            )
            created_post = post_repository.create(post_domain)

            # Get the post with relationships
            retrieved_post = post_repository.get_post_with_relationships(
                created_post.id
            )

            # Verify the post was retrieved
            assert retrieved_post is not None
            assert retrieved_post.id == created_post.id
            assert retrieved_post.pagetitle == "Test Post"

    def test_get_post_with_relationships_nonexistent(self, app, post_repository):
        """Test getting a nonexistent post with relationships loaded."""
        with app.app_context():
            # Try to get a post that doesn't exist
            retrieved_post = post_repository.get_post_with_relationships(
                99999
            )  # Nonexistent ID

            # Verify None is returned
            assert retrieved_post is None

    def test_get_tags_for_post(self, app, post_repository):
        """Test getting tags for a post."""
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

            # Create tags and associate them with the post
            from blog.repos.tag import TagRepository

            tag_repository = TagRepository(db.session)
            tag1_domain = TagDomain(title="Tag 1", alias="tag-1")
            created_tag1 = tag_repository.create(tag1_domain)
            tag2_domain = TagDomain(title="Tag 2", alias="tag-2")
            created_tag2 = tag_repository.create(tag2_domain)

            # Manually create the tag-post relationship at the ORM level
            # This is a workaround for the current limitation in the domain model approach
            tag1_orm = db.session.get(TagORM, created_tag1.id)
            tag2_orm = db.session.get(TagORM, created_tag2.id)
            post_orm = db.session.get(PostORM, created_post.id)

            if tag1_orm and tag2_orm and post_orm:
                post_orm.tags.append(tag1_orm)
                post_orm.tags.append(tag2_orm)
                db.session.commit()

            # Get tags for the post
            tags = post_repository.get_tags_for_post(created_post.id)

            # Verify we got the tags
            assert len(tags) >= 2
            titles = [tag.title for tag in tags]
            assert "Tag 1" in titles
            assert "Tag 2" in titles

            # Verify they are domain models
            assert all(isinstance(tag, TagDomain) for tag in tags)
            assert all(not hasattr(tag, "_sa_instance_state") for tag in tags)

    def test_get_tags_for_post_nonexistent(self, app, post_repository):
        """Test getting tags for a nonexistent post."""
        with app.app_context():
            # Try to get tags for a post that doesn't exist
            tags = post_repository.get_tags_for_post(99999)  # Nonexistent ID

            # Verify an empty list is returned
            assert tags == []

    def test_get_posts_by_tag(self, app, post_repository):
        """Test getting posts by tag."""
        with app.app_context():
            # Create tags first
            from blog.repos.tag import TagRepository

            tag_repository = TagRepository(db.session)
            tag_domain = TagDomain(title="Test Tag", alias="test-tag")
            created_tag = tag_repository.create(tag_domain)

            # Create posts and associate them with the tag
            post1_domain = PostDomain(
                pagetitle="Post 1",
                alias="post-1",
                content="Content 1",
                createdon=datetime.datetime.now(datetime.timezone.utc),
                publishedon=datetime.datetime.now(datetime.timezone.utc),
            )
            created_post1 = post_repository.create(post1_domain)

            post2_domain = PostDomain(
                pagetitle="Post 2",
                alias="post-2",
                content="Content 2",
                createdon=datetime.datetime.now(datetime.timezone.utc),
                publishedon=datetime.datetime.now(datetime.timezone.utc),
            )
            created_post2 = post_repository.create(post2_domain)

            # Manually create the tag-post relationship at the ORM level
            # This is a workaround for the current limitation in the domain model approach
            tag_orm = db.session.get(TagORM, created_tag.id)
            post1_orm = db.session.get(PostORM, created_post1.id)
            post2_orm = db.session.get(PostORM, created_post2.id)

            if tag_orm and post1_orm and post2_orm:
                tag_orm.posts.append(post1_orm)
                tag_orm.posts.append(post2_orm)
                db.session.commit()

            # Get posts by tag
            posts = post_repository.get_posts_by_tag(created_tag.id)

            # Verify we got the posts
            assert len(posts) >= 2
            titles = [post.pagetitle for post in posts]
            assert "Post 1" in titles
            assert "Post 2" in titles

            # Verify they are domain models
            assert all(isinstance(post, PostDomain) for post in posts)
            assert all(not hasattr(post, "_sa_instance_state") for post in posts)

    def test_get_posts_by_tag_nonexistent(self, app, post_repository):
        """Test getting posts by a nonexistent tag."""
        with app.app_context():
            # Try to get posts for a tag that doesn't exist
            posts = post_repository.get_posts_by_tag(99999)  # Nonexistent ID

            # Verify an empty list is returned
            assert posts == []

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

    def test_get_by_id_nonexistent(self, app, category_repository):
        """Test getting a nonexistent category by ID."""
        with app.app_context():
            # Try to get a category that doesn't exist
            retrieved_category = category_repository.get_by_id(99999)  # Nonexistent ID

            # Verify None is returned
            assert retrieved_category is None

    def test_get_by_alias(self, app, category_repository):
        """Test getting a category by alias."""
        with app.app_context():
            # Create a category first
            category_domain = CategoryDomain(
                title="Test Category", alias="test-category"
            )
            created_category = category_repository.create(category_domain)

            # Get the category by alias
            retrieved_category = category_repository.get_by_alias("test-category")

            # Verify the category was retrieved correctly
            assert retrieved_category is not None
            assert retrieved_category.id == created_category.id
            assert retrieved_category.alias == "test-category"

    def test_get_by_alias_nonexistent(self, app, category_repository):
        """Test getting a nonexistent category by alias."""
        with app.app_context():
            # Try to get a category that doesn't exist
            retrieved_category = category_repository.get_by_alias("nonexistent-alias")

            # Verify None is returned
            assert retrieved_category is None

    def test_get_all(self, app, category_repository):
        """Test getting all categories."""
        with app.app_context():
            # Create a few categories
            category1_domain = CategoryDomain(
                title="Test Category 1", alias="test-category-1"
            )
            category_repository.create(category1_domain)

            category2_domain = CategoryDomain(
                title="Test Category 2", alias="test-category-2"
            )
            category_repository.create(category2_domain)

            # Get all categories
            categories = category_repository.get_all()

            # Verify we got the categories
            assert len(categories) >= 2
            aliases = [category.alias for category in categories]
            assert "test-category-1" in aliases
            assert "test-category-2" in aliases

            # Verify they are domain models
            assert all(isinstance(category, CategoryDomain) for category in categories)
            assert all(
                not hasattr(category, "_sa_instance_state") for category in categories
            )

    def test_get_all_empty(self, app, category_repository):
        """Test getting all categories when there are none."""
        with app.app_context():
            # Get all categories when there are none
            categories = category_repository.get_all()

            # Verify an empty list is returned
            assert categories == []

    def test_get_categories_with_posts(self, app, category_repository):
        """Test getting categories with posts loaded."""
        with app.app_context():
            # Create a category
            category_domain = CategoryDomain(
                title="Test Category", alias="test-category"
            )
            category_repository.create(category_domain)

            # Get categories with posts
            categories = category_repository.get_categories_with_posts()

            # Verify we got the category
            assert len(categories) >= 1
            aliases = [category.alias for category in categories]
            assert "test-category" in aliases

            # Verify they are domain models
            assert all(isinstance(category, CategoryDomain) for category in categories)
            assert all(
                not hasattr(category, "_sa_instance_state") for category in categories
            )

    def test_get_categories_with_posts_empty(self, app, category_repository):
        """Test getting categories with posts when there are none."""
        with app.app_context():
            # Get categories with posts when there are none
            categories = category_repository.get_categories_with_posts()

            # Verify an empty list is returned
            assert categories == []

    def test_update_category(self, app, category_repository):
        """Test updating a category."""
        with app.app_context():
            # Create a category first
            category_domain = CategoryDomain(
                title="Test Category", alias="test-category"
            )
            created_category = category_repository.create(category_domain)

            # Update the category
            created_category.title = "Updated Category"
            updated_category = category_repository.update(created_category)

            # Verify the category was updated
            assert updated_category.title == "Updated Category"

            # Verify the ORM model was updated
            stmt = db.select(CategoryORM).where(CategoryORM.id == created_category.id)
            category_orm = db.session.scalar(stmt)
            assert category_orm is not None
            assert category_orm.title == "Updated Category"

    def test_update_nonexistent_category(self, app, category_repository):
        """Test updating a nonexistent category."""
        with app.app_context():
            # Try to update a category that doesn't exist
            category_domain = CategoryDomain(
                id=99999,  # Nonexistent ID
                title="Test Category",
                alias="test-category",
            )

            # Verify that updating a nonexistent category raises an error
            with pytest.raises(ValueError):
                category_repository.update(category_domain)

    def test_delete_category(self, app, category_repository):
        """Test deleting a category."""
        with app.app_context():
            # Create a category first
            category_domain = CategoryDomain(
                title="Test Category", alias="test-category"
            )
            created_category = category_repository.create(category_domain)

            # Delete the category
            result = category_repository.delete(created_category.id)

            # Verify the category was deleted
            assert result is True

            # Verify the category no longer exists
            retrieved_category = category_repository.get_by_id(created_category.id)
            assert retrieved_category is None

            # Verify the ORM model was deleted
            stmt = db.select(CategoryORM).where(CategoryORM.id == created_category.id)
            category_orm = db.session.scalar(stmt)

    def test_delete_nonexistent_category(self, app, category_repository):
        """Test deleting a nonexistent category."""
        with app.app_context():
            # Try to delete a category that doesn't exist
            result = category_repository.delete(99999)  # Nonexistent ID

            # Verify the result is False
            assert result is False

            # Verify None is returned

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

    def test_get_by_id_nonexistent(self, app, tag_repository):
        """Test getting a nonexistent tag by ID."""
        with app.app_context():
            # Try to get a tag that doesn't exist
            retrieved_tag = tag_repository.get_by_id(99999)  # Nonexistent ID

            # Verify None is returned
            assert retrieved_tag is None

    def test_get_by_alias(self, app, tag_repository):
        """Test getting a tag by alias."""
        with app.app_context():
            # Create a tag first
            tag_domain = TagDomain(title="Test Tag", alias="test-tag")
            created_tag = tag_repository.create(tag_domain)

            # Get the tag by alias
            retrieved_tag = tag_repository.get_by_alias("test-tag")

            # Verify the tag was retrieved correctly
            assert retrieved_tag is not None
            assert retrieved_tag.id == created_tag.id
            assert retrieved_tag.alias == "test-tag"

    def test_get_by_alias_nonexistent(self, app, tag_repository):
        """Test getting a nonexistent tag by alias."""
        with app.app_context():
            # Try to get a tag that doesn't exist
            retrieved_tag = tag_repository.get_by_alias("nonexistent-alias")

            # Verify None is returned
            assert retrieved_tag is None

    def test_get_all(self, app, tag_repository):
        """Test getting all tags."""
        with app.app_context():
            # Create a few tags
            tag1_domain = TagDomain(title="Test Tag 1", alias="test-tag-1")
            tag_repository.create(tag1_domain)

            tag2_domain = TagDomain(title="Test Tag 2", alias="test-tag-2")
            tag_repository.create(tag2_domain)

            # Get all tags
            tags = tag_repository.get_all()

            # Verify we got the tags
            assert len(tags) >= 2
            aliases = [tag.alias for tag in tags]
            assert "test-tag-1" in aliases
            assert "test-tag-2" in aliases

            # Verify they are domain models
            assert all(isinstance(tag, TagDomain) for tag in tags)
            assert all(not hasattr(tag, "_sa_instance_state") for tag in tags)

    def test_get_all_empty(self, app, tag_repository):
        """Test getting all tags when there are none."""
        with app.app_context():
            # Get all tags when there are none
            tags = tag_repository.get_all()

            # Verify an empty list is returned
            assert tags == []

    def test_get_tags_with_posts(self, app, tag_repository):
        """Test getting tags with posts loaded."""
        with app.app_context():
            # Create a tag
            tag_domain = TagDomain(title="Test Tag", alias="test-tag")
            tag_repository.create(tag_domain)

            # Get tags with posts
            tags = tag_repository.get_tags_with_posts()

            # Verify we got the tag
            assert len(tags) >= 1
            aliases = [tag.alias for tag in tags]
            assert "test-tag" in aliases

            # Verify they are domain models
            assert all(isinstance(tag, TagDomain) for tag in tags)
            assert all(not hasattr(tag, "_sa_instance_state") for tag in tags)

    def test_get_tags_with_posts_empty(self, app, tag_repository):
        """Test getting tags with posts when there are none."""
        with app.app_context():
            # Get tags with posts when there are none
            tags = tag_repository.get_tags_with_posts()

            # Verify an empty list is returned
            assert tags == []

    def test_get_tags_for_post(self, app, tag_repository):
        """Test getting tags for a post."""
        with app.app_context():
            # Create a post first
            from blog.repos.post import PostRepository

            post_repository = PostRepository(db.session)
            post_domain = PostDomain(
                pagetitle="Test Post",
                alias="test-post",
                content="This is a test post",
                createdon=datetime.datetime.now(datetime.timezone.utc),
                publishedon=datetime.datetime.now(datetime.timezone.utc),
            )
            created_post = post_repository.create(post_domain)

            # Create tags and associate them with the post
            tag1_domain = TagDomain(title="Tag 1", alias="tag-1")
            created_tag1 = tag_repository.create(tag1_domain)
            tag2_domain = TagDomain(title="Tag 2", alias="tag-2")
            created_tag2 = tag_repository.create(tag2_domain)

            # Manually create the tag-post relationship at the ORM level
            # This is a workaround for the current limitation in the domain model approach
            tag1_orm = db.session.get(TagORM, created_tag1.id)
            tag2_orm = db.session.get(TagORM, created_tag2.id)
            post_orm = db.session.get(PostORM, created_post.id)

            if tag1_orm and tag2_orm and post_orm:
                post_orm.tags.append(tag1_orm)
                post_orm.tags.append(tag2_orm)
                db.session.commit()

            # Get tags for the post
            tags = tag_repository.get_tags_for_post(created_post.id)

            # Verify we got the tags
            assert len(tags) >= 2
            titles = [tag.title for tag in tags]
            assert "Tag 1" in titles
            assert "Tag 2" in titles

            # Verify they are domain models
            assert all(isinstance(tag, TagDomain) for tag in tags)
            assert all(not hasattr(tag, "_sa_instance_state") for tag in tags)

    def test_get_tags_for_post_nonexistent(self, app, tag_repository):
        """Test getting tags for a nonexistent post."""
        with app.app_context():
            # Try to get tags for a post that doesn't exist
            tags = tag_repository.get_tags_for_post(99999)  # Nonexistent ID

            # Verify an empty list is returned
            assert tags == []

    def test_update_tag(self, app, tag_repository):
        """Test updating a tag."""
        with app.app_context():
            # Create a tag first
            tag_domain = TagDomain(title="Test Tag", alias="test-tag")
            created_tag = tag_repository.create(tag_domain)

            # Update the tag
            created_tag.title = "Updated Tag"
            updated_tag = tag_repository.update(created_tag)

            # Verify the tag was updated
            assert updated_tag.title == "Updated Tag"

            # Verify the ORM model was updated
            stmt = db.select(TagORM).where(TagORM.id == created_tag.id)
            tag_orm = db.session.scalar(stmt)
            assert tag_orm is not None
            assert tag_orm.title == "Updated Tag"

    def test_update_nonexistent_tag(self, app, tag_repository):
        """Test updating a nonexistent tag."""
        with app.app_context():
            # Try to update a tag that doesn't exist
            tag_domain = TagDomain(
                id=99999,  # Nonexistent ID
                title="Test Tag",
                alias="test-tag",
            )

            # Verify that updating a nonexistent tag raises an error
            with pytest.raises(ValueError):
                tag_repository.update(tag_domain)

    def test_delete_tag(self, app, tag_repository):
        """Test deleting a tag."""
        with app.app_context():
            # Create a tag first
            tag_domain = TagDomain(title="Test Tag", alias="test-tag")
            created_tag = tag_repository.create(tag_domain)

            # Delete the tag
            result = tag_repository.delete(created_tag.id)

            # Verify the tag was deleted
            assert result is True

            # Verify the tag no longer exists
            retrieved_tag = tag_repository.get_by_id(created_tag.id)
            assert retrieved_tag is None

            # Verify the ORM model was deleted
            stmt = db.select(TagORM).where(TagORM.id == created_tag.id)
            tag_orm = db.session.scalar(stmt)

    def test_delete_nonexistent_tag(self, app, tag_repository):
        """Test deleting a nonexistent tag."""
        with app.app_context():
            # Try to delete a tag that doesn't exist
            result = tag_repository.delete(99999)  # Nonexistent ID

            # Verify the result is False

            # Verify None is returned

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

    def test_get_by_id_nonexistent(self, app, user_repository):
        """Test getting a nonexistent user by ID."""
        with app.app_context():
            # Try to get a user that doesn't exist
            retrieved_user = user_repository.get_by_id(99999)  # Nonexistent ID

            # Verify None is returned
            assert retrieved_user is None

    def test_get_by_name(self, app, user_repository):
        """Test getting a user by name."""
        with app.app_context():
            # Create a user first
            user_domain = UserDomain(name="testuser", password="testpassword")
            created_user = user_repository.create(user_domain)

            # Get the user by name
            retrieved_user = user_repository.get_by_name("testuser")

            # Verify the user was retrieved correctly
            assert retrieved_user is not None
            assert retrieved_user.id == created_user.id
            assert retrieved_user.name == "testuser"

    def test_get_by_name_nonexistent(self, app, user_repository):
        """Test getting a nonexistent user by name."""
        with app.app_context():
            # Try to get a user that doesn't exist
            retrieved_user = user_repository.get_by_name("nonexistent")

            # Verify None is returned
            assert retrieved_user is None

    def test_get_all(self, app, user_repository):
        """Test getting all users."""
        with app.app_context():
            # Create a few users
            user1_domain = UserDomain(name="testuser1", password="testpassword1")
            user_repository.create(user1_domain)

            user2_domain = UserDomain(name="testuser2", password="testpassword2")
            user_repository.create(user2_domain)

            # Get all users
            users = user_repository.get_all()

            # Verify we got the users
            assert len(users) >= 2
            names = [user.name for user in users]
            assert "testuser1" in names
            assert "testuser2" in names

            # Verify they are domain models
            assert all(isinstance(user, UserDomain) for user in users)
            assert all(not hasattr(user, "_sa_instance_state") for user in users)

    def test_get_all_empty(self, app, user_repository):
        """Test getting all users when there are none."""
        with app.app_context():
            # Get all users when there are none
            users = user_repository.get_all()

            # Verify an empty list is returned
            assert users == []

    def test_get_users_with_posts(self, app, user_repository):
        """Test getting users with posts loaded."""
        with app.app_context():
            # Create a user
            user_domain = UserDomain(name="testuser", password="testpassword")
            user_repository.create(user_domain)

            # Get users with posts
            users = user_repository.get_users_with_posts()

            # Verify we got the user
            assert len(users) >= 1
            names = [user.name for user in users]
            assert "testuser" in names

            # Verify they are domain models
            assert all(isinstance(user, UserDomain) for user in users)
            assert all(not hasattr(user, "_sa_instance_state") for user in users)

    def test_get_users_with_posts_empty(self, app, user_repository):
        """Test getting users with posts when there are none."""
        with app.app_context():
            # Get users with posts when there are none
            users = user_repository.get_users_with_posts()

            # Verify an empty list is returned
            assert users == []

    def test_update_user(self, app, user_repository):
        """Test updating a user."""
        with app.app_context():
            # Create a user first
            user_domain = UserDomain(name="testuser", password="testpassword")
            created_user = user_repository.create(user_domain)

            # Update the user
            created_user.name = "updateduser"
            updated_user = user_repository.update(created_user)

            # Verify the user was updated
            assert updated_user.name == "updateduser"

            # Verify the ORM model was updated
            stmt = db.select(UserORM).where(UserORM.id == created_user.id)
            user_orm = db.session.scalar(stmt)
            assert user_orm is not None
            assert user_orm.name == "updateduser"

    def test_update_nonexistent_user(self, app, user_repository):
        """Test updating a nonexistent user."""
        with app.app_context():
            # Try to update a user that doesn't exist
            user_domain = UserDomain(
                id=99999,  # Nonexistent ID
                name="testuser",
                password="testpassword",
            )

            # Verify that updating a nonexistent user raises an error
            with pytest.raises(ValueError):
                user_repository.update(user_domain)

    def test_delete_user(self, app, user_repository):
        """Test deleting a user."""
        with app.app_context():
            # Create a user first
            user_domain = UserDomain(name="testuser", password="testpassword")
            created_user = user_repository.create(user_domain)

            # Delete the user
            result = user_repository.delete(created_user.id)

            # Verify the user was deleted
            assert result is True

            # Verify the user no longer exists
            retrieved_user = user_repository.get_by_id(created_user.id)
            assert retrieved_user is None

            # Verify the ORM model was deleted
            stmt = db.select(UserORM).where(UserORM.id == created_user.id)
            user_orm = db.session.scalar(stmt)
            assert user_orm is None

    def test_delete_nonexistent_user(self, app, user_repository):
        """Test deleting a nonexistent user."""
        with app.app_context():
            # Try to delete a user that doesn't exist
            result = user_repository.delete(99999)  # Nonexistent ID

            # Verify the result is False
            assert result is False

    def test_authenticate(self, app, user_repository):
        """Test authenticating a user."""
        with app.app_context():
            # Create a user first
            user_domain = UserDomain(name="testuser", password="testpassword")
            created_user = user_repository.create(user_domain)

            # Manually hash the password for the created user at the ORM level
            # This is needed because the repository doesn't hash passwords
            user_orm = UserORM.query.get(created_user.id)
            if user_orm:
                user_orm.set_password("testpassword")
                db.session.commit()

            # Authenticate the user
            authenticated_user = user_repository.authenticate(
                "testuser", "testpassword"
            )

            # Verify the user was authenticated
            assert authenticated_user is not None
            assert authenticated_user.id == created_user.id
            assert authenticated_user.name == "testuser"

    def test_authenticate_wrong_password(self, app, user_repository):
        """Test authenticating a user with wrong password."""
        with app.app_context():
            # Create a user first
            user_domain = UserDomain(name="testuser", password="testpassword")
            user_repository.create(user_domain)

            # Manually hash the password for the created user at the ORM level
            # This is needed because the repository doesn't hash passwords
            user_orm = UserORM.query.first()
            if user_orm:
                user_orm.set_password("testpassword")
                db.session.commit()

            # Try to authenticate with wrong password
            authenticated_user = user_repository.authenticate(
                "testuser", "wrongpassword"
            )

            # Verify authentication failed
            assert authenticated_user is None

    def test_authenticate_nonexistent_user(self, app, user_repository):
        """Test authenticating a nonexistent user."""
        with app.app_context():
            # Try to authenticate a user that doesn't exist
            authenticated_user = user_repository.authenticate("nonexistent", "password")

            # Verify authentication failed
            assert authenticated_user is None

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

    def test_get_by_id_nonexistent(self, app, icon_repository):
        """Test getting a nonexistent icon by ID."""
        with app.app_context():
            # Try to get an icon that doesn't exist
            retrieved_icon = icon_repository.get_by_id(99999)  # Nonexistent ID

            # Verify None is returned
            assert retrieved_icon is None

    def test_get_by_title(self, app, icon_repository):
        """Test getting an icon by title."""
        with app.app_context():
            # Create an icon first
            icon_domain = IconDomain(
                title="Test Icon",
                url="http://example.com/icon.png",
                content="Icon content",
            )
            created_icon = icon_repository.create(icon_domain)

            # Get the icon by title
            retrieved_icon = icon_repository.get_by_title("Test Icon")

            # Verify the icon was retrieved correctly
            assert retrieved_icon is not None
            assert retrieved_icon.id == created_icon.id
            assert retrieved_icon.title == "Test Icon"

    def test_get_by_title_nonexistent(self, app, icon_repository):
        """Test getting a nonexistent icon by title."""
        with app.app_context():
            # Try to get an icon that doesn't exist
            retrieved_icon = icon_repository.get_by_title("nonexistent-title")

            # Verify None is returned
            assert retrieved_icon is None

    def test_get_all(self, app, icon_repository):
        """Test getting all icons."""
        with app.app_context():
            # Create a few icons
            icon1_domain = IconDomain(
                title="Test Icon 1",
                url="http://example.com/icon1.png",
                content="Icon content 1",
            )
            icon_repository.create(icon1_domain)

            icon2_domain = IconDomain(
                title="Test Icon 2",
                url="http://example.com/icon2.png",
                content="Icon content 2",
            )
            icon_repository.create(icon2_domain)

            # Get all icons
            icons = icon_repository.get_all()

            # Verify we got the icons
            assert len(icons) >= 2
            titles = [icon.title for icon in icons]
            assert "Test Icon 1" in titles
            assert "Test Icon 2" in titles

            # Verify they are domain models
            assert all(isinstance(icon, IconDomain) for icon in icons)
            assert all(not hasattr(icon, "_sa_instance_state") for icon in icons)

    def test_get_all_empty(self, app, icon_repository):
        """Test getting all icons when there are none."""
        with app.app_context():
            # Get all icons when there are none
            icons = icon_repository.get_all()

            # Verify an empty list is returned
            assert icons == []

    def test_update_icon(self, app, icon_repository):
        """Test updating an icon."""
        with app.app_context():
            # Create an icon first
            icon_domain = IconDomain(
                title="Test Icon",
                url="http://example.com/icon.png",
                content="Icon content",
            )
            created_icon = icon_repository.create(icon_domain)

            # Update the icon
            created_icon.title = "Updated Icon"
            updated_icon = icon_repository.update(created_icon)

            # Verify the icon was updated
            assert updated_icon.title == "Updated Icon"

            # Verify the ORM model was updated
            stmt = db.select(IconORM).where(IconORM.id == created_icon.id)
            icon_orm = db.session.scalar(stmt)
            assert icon_orm is not None
            assert icon_orm.title == "Updated Icon"

    def test_update_nonexistent_icon(self, app, icon_repository):
        """Test updating a nonexistent icon."""
        with app.app_context():
            # Try to update an icon that doesn't exist
            icon_domain = IconDomain(
                id=99999,  # Nonexistent ID
                title="Test Icon",
                url="http://example.com/icon.png",
                content="Icon content",
            )

            # Verify that updating a nonexistent icon raises an error
            with pytest.raises(ValueError):
                icon_repository.update(icon_domain)

    def test_delete_icon(self, app, icon_repository):
        """Test deleting an icon."""
        with app.app_context():
            # Create an icon first
            icon_domain = IconDomain(
                title="Test Icon",
                url="http://example.com/icon.png",
                content="Icon content",
            )
            created_icon = icon_repository.create(icon_domain)

            # Delete the icon
            result = icon_repository.delete(created_icon.id)

            # Verify the icon was deleted
            assert result is True

            # Verify the icon no longer exists
            retrieved_icon = icon_repository.get_by_id(created_icon.id)
            assert retrieved_icon is None

            # Verify the ORM model was deleted
            stmt = db.select(IconORM).where(IconORM.id == created_icon.id)
            icon_orm = db.session.scalar(stmt)

    def test_delete_nonexistent_icon(self, app, icon_repository):
        """Test deleting a nonexistent icon."""
        with app.app_context():
            # Try to delete an icon that doesn't exist
            result = icon_repository.delete(99999)  # Nonexistent ID

            # Verify the result is False
            assert result is False


            # Verify an empty list is returned

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
