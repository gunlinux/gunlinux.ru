from typing import TYPE_CHECKING, cast

import flask_login
from flask import Blueprint, Response, flash, redirect, render_template, url_for
from flask_login import (
    current_user,
    login_user,
)

from blog.auth.adapter import auth_adapter
from blog.user.forms import LoginForm

if TYPE_CHECKING:
    from flask import Response


user = Blueprint("user", __name__)


@user.route("/login", methods=["GET", "POST"])
def login() -> Response | str:
    if current_user.is_authenticated:
        return cast("Response", redirect("/"))
    form = LoginForm()
    if form.validate_on_submit():
        # Check that form data is not None before using it
        name = form.name.data
        password = form.password.data
        if name is not None and password is not None:
            # Use the authentication adapter for Flask-Login integration
            user_orm = auth_adapter.authenticate_and_login(name, password)
            if user_orm:
                login_user(user_orm)
                return cast("Response", redirect(url_for("admin.index")))
        flash("invalid user or password")
        return cast("Response", redirect(url_for("user.login")))
    return render_template("login.html", form=form)


@user.route("/logout")
def logout() -> Response:
    flask_login.logout_user()
    return cast("Response", redirect(url_for("post.index")))
