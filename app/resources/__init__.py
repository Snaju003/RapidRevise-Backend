# app/resources/__init__.py

from flask import Blueprint

resources_bp = Blueprint('resources_bp', __name__)

# Import routes so they get registered with the blueprint
from . import routes