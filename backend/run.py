#!/usr/bin/env python3
"""FlockYou API Server - Main entry point."""
from app import create_app

app, socketio = create_app()

if __name__ == '__main__':
    print("="*60)
    print("  FlockYou API Server v2.0")
    print("="*60)
    print("Server will be available at: http://localhost:5000")
    print("API Documentation: http://localhost:5000/api/health")
    print("Press Ctrl+C to stop the server")
    print("="*60)

    try:
        socketio.run(
            app,
            debug=False,
            host='0.0.0.0',
            port=5000,
            allow_unsafe_werkzeug=True,
        )
    except KeyboardInterrupt:
        print("\nShutting down server...")
        # Clean up connections
        gps = app.config.get('gps_service')
        flock = app.config.get('flock_service')

        if gps:
            gps.disconnect()
        if flock:
            flock.disconnect()

        print("Server stopped.")
