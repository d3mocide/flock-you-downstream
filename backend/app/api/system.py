"""System API endpoints - settings and health."""
from flask import request, jsonify, current_app
from . import api_bp


@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'flockyou-api',
        'version': '2.0.0',
    })


@api_bp.route('/settings', methods=['GET'])
def get_settings():
    """Get current settings."""
    storage = current_app.config['storage_service']
    return jsonify(storage.settings)


@api_bp.route('/settings', methods=['POST'])
def update_settings():
    """Update settings."""
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    storage = current_app.config['storage_service']
    updated = storage.update_settings(data)
    return jsonify({'status': 'success', 'settings': updated})
