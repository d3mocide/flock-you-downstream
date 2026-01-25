"""FlockYou API Application Factory."""
import os
from flask import Flask, render_template
from flask_socketio import SocketIO

from .services.gps_service import GPSService
from .services.flock_service import FlockService
from .services.storage_service import StorageService
from .services.oui_service import OUIService


def create_app(config: dict = None) -> tuple[Flask, SocketIO]:
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder='templates')

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'flockyou_dev_key_2024')

    if config:
        app.config.update(config)

    # Initialize SocketIO
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode='threading',
        logger=False,
        engineio_logger=False,
    )

    # Initialize services
    data_dir = app.config.get('DATA_DIR', 'data')
    oui_file = app.config.get('OUI_FILE', 'oui.txt')

    storage_service = StorageService(data_dir=data_dir)
    gps_service = GPSService()
    flock_service = FlockService()
    oui_service = OUIService(oui_file=oui_file)

    # Store services in app config for access in routes
    app.config['storage_service'] = storage_service
    app.config['gps_service'] = gps_service
    app.config['flock_service'] = flock_service
    app.config['oui_service'] = oui_service
    app.config['socketio'] = socketio

    # Wire up service callbacks
    _setup_service_callbacks(app, socketio, storage_service, gps_service, flock_service, oui_service)

    # Register blueprints
    from .api import api_bp
    app.register_blueprint(api_bp)

    # Register SocketIO events
    _setup_socketio_events(socketio, app)

    # Main route (dashboard)
    @app.route('/')
    def index():
        return render_template('index.html')

    return app, socketio


def _setup_service_callbacks(app, socketio, storage, gps, flock, oui):
    """Set up callbacks between services and SocketIO."""

    def on_gps_update(data):
        with app.app_context():
            try:
                socketio.emit('gps_update', data.to_dict())
            except Exception as e:
                print(f"GPS emit error: {e}")

    def on_gps_disconnect():
        with app.app_context():
            try:
                socketio.emit('gps_disconnected', {})
            except Exception as e:
                print(f"GPS disconnect emit error: {e}")

    def on_gps_raw(line):
        with app.app_context():
            try:
                socketio.emit('serial_data', line, room='serial_terminal')
            except Exception:
                pass

    gps.set_callbacks(
        on_update=on_gps_update,
        on_disconnect=on_gps_disconnect,
        on_raw_data=on_gps_raw,
    )

    def on_detection(data):
        with app.app_context():
            # Add GPS data
            gps_data = gps.current_data
            if gps_data and gps_data.is_valid():
                data['gps'] = gps_data.to_dict()

            # Add manufacturer
            if 'mac_address' in data:
                data['manufacturer'] = oui.lookup(data['mac_address'])

            # Store detection
            detection = storage.add_detection(data)

            # Emit to clients
            try:
                socketio.emit('new_detection', detection)
            except Exception as e:
                print(f"Detection emit error: {e}")

    def on_flock_raw(line):
        with app.app_context():
            try:
                socketio.emit('serial_data', line, room='serial_terminal')
            except Exception:
                pass

    def on_flock_disconnect():
        with app.app_context():
            try:
                socketio.emit('flock_disconnected', {})
            except Exception:
                pass

    def on_flock_reconnect(port):
        with app.app_context():
            try:
                socketio.emit('flock_reconnected', {'port': port})
            except Exception:
                pass

    flock.set_callbacks(
        on_detection=on_detection,
        on_raw_data=on_flock_raw,
        on_disconnect=on_flock_disconnect,
        on_reconnect=on_flock_reconnect,
    )


def _setup_socketio_events(socketio, app):
    """Set up SocketIO event handlers."""
    from flask_socketio import emit, join_room, leave_room
    from flask import request

    @socketio.on('connect')
    def handle_connect():
        print(f"Client connected: {request.sid}")

    @socketio.on('disconnect')
    def handle_disconnect():
        print(f"Client disconnected: {request.sid}")
        try:
            leave_room('serial_terminal')
        except Exception:
            pass

    @socketio.on('heartbeat')
    def handle_heartbeat():
        try:
            emit('heartbeat_ack')
        except Exception as e:
            print(f"Heartbeat error: {e}")

    @socketio.on('request_serial_terminal')
    def handle_serial_terminal_request(data):
        port = data.get('port') if data else None
        flock_service = app.config['flock_service']

        if not port:
            emit('serial_error', {'message': 'No port specified'})
            return

        if not flock_service.is_connected or flock_service.port != port:
            emit('serial_error', {'message': 'Device not connected. Connect to the Sniffer device first.'})
            return

        try:
            join_room('serial_terminal')
            emit('serial_connected')

            # Send recent buffer
            for line in flock_service.buffer[-50:]:
                emit('serial_data', line)

            print(f"Serial terminal connected for {request.sid}")

        except Exception as e:
            emit('serial_error', {'message': f'Failed to start terminal: {str(e)}'})
