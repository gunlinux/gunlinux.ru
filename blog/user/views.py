import flask_login
from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_user

from blog.auth.adapter import auth_adapter
from blog.extensions import login_manager
from blog.user.forms import LoginForm


user = Blueprint("user", __name__)


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    # Use the authentication adapter for Flask-Login integration
    return auth_adapter.load_user(int(user_id))


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
            # Use the authentication adapter for Flask-Login integration
            user_orm = auth_adapter.authenticate_and_login(name, password)
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
