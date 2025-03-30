from flask import Blueprint

bp = Blueprint('study_plan', __name__)

from . import routes