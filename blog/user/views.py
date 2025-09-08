import flask_login
from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_user

from blog.extensions import login_manager
from blog.user.forms import LoginForm
from blog.services.factory import ServiceFactory


user = Blueprint("user", __name__)


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    # For Flask-Login compatibility, we need to return an ORM model
    user_service = ServiceFactory.create_user_service()
    user = user_service.get_user_by_id(int(user_id))
    if user:
        # This is one of the few places where we directly access the service layer
        # to get an ORM model because Flask-Login requires an ORM model
        return user_service.get_user_orm_by_id(int(user_id))
    return None


@user.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect("/")
    form = LoginForm()
    if form.validate_on_submit():
        # Check that form data is not None before using it
        name = form.name.data
        password = form.password.data
        if name is not None and password is not None:
            user_service = ServiceFactory.create_user_service()
            user = user_service.authenticate_user(name, password)

            if user:
                # Get the ORM model directly from service layer for Flask-Login
                # This is one of the few places where we directly access the service layer
                # to get an ORM model because Flask-Login requires an ORM model
                user_orm = user_service.get_user_orm_by_name(name)
                if user_orm:
                    login_user(user_orm)
                    return redirect(url_for("admin.index"))
        flash("invalid user o password")
        return redirect(url_for("user.login"))
    return render_template("login.html", form=form)


@user.route("/logout")
def logout():
    flask_login.logout_user()
    return redirect(url_for("post.index"))
