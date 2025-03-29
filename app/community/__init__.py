# community/__init__.py
from flask import Blueprint

# Create a Blueprint for the community module
community_bp = Blueprint('community_bp', __name__)

# Import routes to attach them to the blueprint
from . import routes