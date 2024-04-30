from flask import Blueprint, redirect
from flask_login import current_user


user_blueprint = Blueprint("userb", __name__)


@user_blueprint.route('/login')
def login():
    if current_user.is_authenticated():
        return redirect('/')
    return 'login my ass'
