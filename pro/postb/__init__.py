from flask import Blueprint

postb = Blueprint('postb', __name__)

from . import views
