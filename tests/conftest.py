import eventlet
eventlet.monkey_patch() # Apply monkey patch globally
import pytest
from nebula import Nebula

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = Nebula(__name__, "localhost", 8000)
    return app

@pytest.fixture
def client(app):
    """A test client for the app."""
    from werkzeug.test import Client
    from werkzeug.wrappers import Response
    return Client(app, Response)

@pytest.fixture
def socketio_server(app):
    import eventlet

    import socketio
    import time

    # Use a dynamically assigned port
    listener = eventlet.listen(('localhost', 0))
    port = listener.getsockname()[1]
    server_url = f"http://localhost:{port}"

    # Set up the Nebula app and Socket.IO WSGI app
    # Re-initialize app to ensure it's fresh for the socketio test
    app = Nebula(__name__, "localhost", port) 
    wsgi_app = socketio.WSGIApp(app.sio, app)

    # Start the server in a background thread
    server_thread = eventlet.spawn(eventlet.wsgi.server, listener, wsgi_app)

    # Wait for the server to be ready
    sio_client_check = socketio.Client(request_timeout=10)
    connected = False
    for i in range(10): # Try connecting for up to 10 seconds (10 * 1 second sleep)
        try:
            sio_client_check.connect(server_url, wait=False, wait_timeout=1)
            if sio_client_check.connected:
                connected = True
                break
        except Exception as e:
            print(f"Socket.IO server readiness check attempt {i+1}/10 failed: {e}")
            time.sleep(1)
    
    if not connected:
        server_thread.kill()
        try:
            app.stop()
        except Exception:
            pass
        raise RuntimeError(f"Socket.IO server failed to start on {server_url} for testing")
    
    sio_client_check.disconnect() # Disconnect the check client
    time.sleep(0.1) # Give server a moment to process disconnect

    yield app, server_url # Provide the app instance and server URL to tests

    # Teardown
    try:
        app.stop() # Ensure Nebula app's server is stopped
    except Exception:
        pass
    server_thread.kill() # Kill the eventlet server thread
    time.sleep(0.1) # Give it a moment to clean up
