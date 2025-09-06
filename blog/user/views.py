import flask_login
import sqlalchemy as sa
from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_user

from blog.extensions import db, login_manager
from blog.user.forms import LoginForm
from blog.user.models import User
from blog.services.factory import ServiceFactory


user_blueprint = Blueprint("userb", __name__)


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    # Use service layer instead of direct database access
    user_service = ServiceFactory.create_user_service()
    return user_service.get_user_by_id_orm(int(user_id))


@user_blueprint.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect("/")
    form = LoginForm()
    if form.validate_on_submit():
        # Use service layer instead of direct database access
        user_service = ServiceFactory.create_user_service()
        user = user_service.authenticate_user(form.name.data, form.password.data)

        if user:
            # Convert domain model to ORM model for Flask-Login
            user_orm = user_service._to_orm_model(user)
            login_user(user_orm)
            return redirect(url_for("admin.index"))
        flash("invalid user o password")
        return redirect(url_for("userb.login"))
    return render_template("login.html", form=form)


@user_blueprint.route("/logout")
def logout():
    flask_login.logout_user()
    return redirect(url_for("postb.index"))
