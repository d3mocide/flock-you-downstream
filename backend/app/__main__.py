"""FlockYou API entry point for python -m app."""
from . import create_app

if __name__ == '__main__':
    app, socketio = create_app()
    print("Starting Flock You API server...")
    print("Server will be available at: http://localhost:5000")
    print("Press Ctrl+C to stop the server")

    try:
        socketio.run(app, debug=False, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\nShutting down server...")
        print("Server stopped.")
