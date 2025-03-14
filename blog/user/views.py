import flask_login
import sqlalchemy as sa
from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_user

from blog.extensions import db
from blog.user.forms import LoginForm
from blog.user.models import User

user_blueprint = Blueprint("userb", __name__)


@user_blueprint.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect("/")
    form = LoginForm()
    if form.validate_on_submit():
        user_query = sa.select(User).where(User.name == form.name.data)
        user = db.session.scalars(user_query).first()

        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for("admin.index"))
        flash("invalid user o password")
        return redirect(url_for("userb.login"))
    return render_template("login.html", form=form)


@user_blueprint.route("/logout")
def logout():
    flask_login.logout_user()
    return redirect(url_for("postb.index"))
