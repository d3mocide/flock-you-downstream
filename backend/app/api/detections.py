"""Detections API endpoints."""
from flask import request, jsonify, current_app
from . import api_bp


@api_bp.route('/detections', methods=['GET'])
def get_detections():
    """Get all detections with optional filtering."""
    filter_type = request.args.get('filter', 'all')
    data_type = request.args.get('type', 'session')

    storage = current_app.config['storage_service']

    if data_type == 'cumulative':
        source_data = storage.cumulative_detections
    else:
        source_data = storage.session_detections

    if filter_type == 'all':
        return jsonify(source_data)
    else:
        filtered = [d for d in source_data if d.get('detection_method') == filter_type]
        return jsonify(filtered)


@api_bp.route('/detections', methods=['POST'])
def add_detection():
    """Add a new detection (typically from device)."""
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    storage = current_app.config['storage_service']
    gps_service = current_app.config['gps_service']
    oui_service = current_app.config['oui_service']

    # Add GPS data if available
    gps_data = gps_service.current_data
    if gps_data and gps_data.is_valid():
        data['gps'] = gps_data.to_dict()

    # Add manufacturer info
    if 'mac_address' in data:
        data['manufacturer'] = oui_service.lookup(data['mac_address'])

    detection = storage.add_detection(data)

    # Emit via SocketIO
    socketio = current_app.config.get('socketio')
    if socketio:
        socketio.emit('new_detection', detection)

    return jsonify({'status': 'success', 'id': detection.get('id')})


@api_bp.route('/detections/clear', methods=['POST'])
def clear_detections():
    """Clear session detections."""
    storage = current_app.config['storage_service']
    storage.clear_session()

    socketio = current_app.config.get('socketio')
    if socketio:
        socketio.emit('detections_cleared', {})

    return jsonify({'status': 'success', 'message': 'Session detections cleared'})


@api_bp.route('/detection/alias', methods=['POST'])
def update_alias():
    """Update detection alias."""
    data = request.json
    detection_id = data.get('id')
    alias = data.get('alias', '').strip()

    if detection_id is None:
        return jsonify({'status': 'error', 'message': 'Detection ID required'}), 400

    storage = current_app.config['storage_service']
    detection = storage.update_alias(detection_id, alias)

    if detection:
        socketio = current_app.config.get('socketio')
        if socketio:
            socketio.emit('detection_updated', detection)
        return jsonify({'status': 'success', 'message': 'Alias updated'})

    return jsonify({'status': 'error', 'message': 'Detection not found'}), 404


@api_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get detection statistics."""
    storage = current_app.config['storage_service']
    return jsonify(storage.get_stats())


@api_bp.route('/test/detection', methods=['POST'])
def test_detection():
    """Add a test detection for debugging."""
    from datetime import datetime

    if request.is_json:
        sample = request.json
        sample.setdefault('detection_method', 'probe_request')
        sample.setdefault('protocol', 'wifi')
        sample.setdefault('mac_address', 'AA:BB:CC:DD:EE:FF')
        sample.setdefault('detection_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        sample.setdefault('timestamp', datetime.now().isoformat())
    else:
        sample = {
            'detection_method': 'probe_request',
            'protocol': 'wifi',
            'mac_address': 'AA:BB:CC:DD:EE:FF',
            'ssid': 'TestNetwork',
            'rssi': -45,
            'signal_strength': 'Excellent',
            'channel': 6,
            'detection_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'timestamp': datetime.now().isoformat(),
        }

    storage = current_app.config['storage_service']
    oui_service = current_app.config['oui_service']

    sample['manufacturer'] = oui_service.lookup(sample.get('mac_address', ''))
    detection = storage.add_detection(sample)

    socketio = current_app.config.get('socketio')
    if socketio:
        socketio.emit('new_detection', detection)

    return jsonify({'status': 'success', 'message': 'Test detection added'})
