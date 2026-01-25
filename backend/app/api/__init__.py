# API package
from flask import Blueprint

# Create main API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Import and register sub-blueprints after creation to avoid circular imports
from . import detections, devices, system, exports, oui

__all__ = ['api_bp']
