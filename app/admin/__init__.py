from typing import override

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy.ext.asyncio import AsyncEngine

from app.auth.jwt import COOKIE_NAME, create_access_token, decode_token
from app.infrastructure.session import AsyncSessionLocal
from app.models.category import Category
from app.models.post import Icon, Post
from app.models.tag import Tag
from app.models.user import User
from app.repositories.user import UserRepository


class AdminAuth(AuthenticationBackend):
    @override
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = str(form.get("username", ""))
        password = str(form.get("password", ""))
        async with AsyncSessionLocal() as session:
            repo = UserRepository(session)
            user = await repo.authenticate(username, password)
        if not user:
            return False
        token = create_access_token(user.name)
        request.session.update({COOKIE_NAME: token})
        return True

    @override
    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    @override
    async def authenticate(self, request: Request) -> bool | RedirectResponse:
        token = request.session.get(COOKIE_NAME)
        if not token:
            return RedirectResponse(request.url_for("admin:login"), status_code=302)
        username = decode_token(token)
        if not username:
            return RedirectResponse(request.url_for("admin:login"), status_code=302)
        return True


class PostAdmin(ModelView, model=Post):
    column_list = [
        Post.id,
        Post.pagetitle,
        Post.alias,
        Post.publishedon,
        Post.category_id,
    ]
    column_searchable_list = [Post.pagetitle, Post.alias]
    column_sortable_list = [Post.id, Post.publishedon]
    name = "Post"
    name_plural = "Posts"
    icon = "fa-solid fa-file-text"
    create_template = "sqladmin/post_create.html"
    edit_template = "sqladmin/post_edit.html"


class CategoryAdmin(ModelView, model=Category):
    column_list = [Category.id, Category.title, Category.alias, Category.page]
    name = "Category"
    name_plural = "Categories"
    icon = "fa-solid fa-folder"


class TagAdmin(ModelView, model=Tag):
    column_list = [Tag.id, Tag.title, Tag.alias]
    name = "Tag"
    name_plural = "Tags"
    icon = "fa-solid fa-tag"


class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.name, User.createdon]
    form_excluded_columns = [User.password]
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"


class IconAdmin(ModelView, model=Icon):
    column_list = [Icon.id, Icon.title, Icon.url]
    name = "Icon"
    name_plural = "Icons"
    icon = "fa-solid fa-image"


def create_admin(app: FastAPI, engine: AsyncEngine) -> Admin:
    authentication_backend = AdminAuth(secret_key="admin-secret-fallback")
    admin = Admin(
        app,
        engine,
        authentication_backend=authentication_backend,
        templates_dir="app/templates",
    )
    admin.add_view(PostAdmin)
    admin.add_view(CategoryAdmin)
    admin.add_view(TagAdmin)
    admin.add_view(UserAdmin)
    admin.add_view(IconAdmin)
    return admin
