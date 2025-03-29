from flask import Blueprint

examprep_bp = Blueprint('examprep_bp', __name__)

from . import routes