"""Devices API endpoints - GPS and Flock device management."""
from flask import request, jsonify, current_app
from . import api_bp


@api_bp.route('/status', methods=['GET'])
def get_status():
    """Get connection status of all devices."""
    gps_service = current_app.config['gps_service']
    flock_service = current_app.config['flock_service']

    return jsonify({
        'gps_connected': gps_service.is_connected,
        'gps_port': gps_service.port,
        'flock_connected': flock_service.is_connected,
        'flock_port': flock_service.port,
    })


# ============ GPS Endpoints ============

@api_bp.route('/gps/ports', methods=['GET'])
def get_gps_ports():
    """Get available serial ports for GPS."""
    from ..services.gps_service import GPSService
    return jsonify(GPSService.list_ports())


@api_bp.route('/gps/connect', methods=['POST'])
def connect_gps():
    """Connect to GPS dongle."""
    data = request.json
    port = data.get('port')

    if not port:
        return jsonify({'status': 'error', 'message': 'Port required'}), 400

    gps_service = current_app.config['gps_service']
    result = gps_service.connect(port)

    if result.get('success'):
        return jsonify({'status': 'success', 'message': f"Connected to {port}"})
    else:
        return jsonify({'status': 'error', 'message': result.get('error')}), 400


@api_bp.route('/gps/disconnect', methods=['POST'])
def disconnect_gps():
    """Disconnect GPS dongle."""
    gps_service = current_app.config['gps_service']
    gps_service.disconnect()
    return jsonify({'status': 'success', 'message': 'GPS disconnected'})


# ============ Flock Device Endpoints ============

@api_bp.route('/flock/ports', methods=['GET'])
def get_flock_ports():
    """Get available serial ports for Flock device."""
    from ..services.flock_service import FlockService
    return jsonify(FlockService.list_ports())


@api_bp.route('/flock/connect', methods=['POST'])
def connect_flock():
    """Connect to Flock device."""
    data = request.json
    port = data.get('port')

    if not port:
        return jsonify({'status': 'error', 'message': 'Port required'}), 400

    flock_service = current_app.config['flock_service']
    result = flock_service.connect(port)

    if result.get('success'):
        return jsonify({'status': 'success', 'message': f"Connected to Flock device on {port}"})
    else:
        return jsonify({'status': 'error', 'message': result.get('error')}), 400


@api_bp.route('/flock/disconnect', methods=['POST'])
def disconnect_flock():
    """Disconnect Flock device."""
    flock_service = current_app.config['flock_service']
    flock_service.disconnect()
    return jsonify({'status': 'success', 'message': 'Flock device disconnected'})
