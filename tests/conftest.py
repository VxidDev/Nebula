import eventlet
eventlet.monkey_patch()

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
    import socketio as sio_lib
    import time

    listener = eventlet.listen(("localhost", 0))
    port = listener.getsockname()[1]
    server_url = f"http://localhost:{port}"

    app = Nebula(__name__, "localhost", port)
    wsgi_app = sio_lib.WSGIApp(app.sio, app)

    server_thread = eventlet.spawn(eventlet_wsgi_server, listener, wsgi_app)

    # Wait for the server to be ready
    sio_client_check = sio_lib.Client(request_timeout=10)
    connected = False
    for i in range(10):
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
        raise RuntimeError(
            f"Socket.IO server failed to start on {server_url} for testing"
        )

    sio_client_check.disconnect()
    time.sleep(0.1)

    yield app, server_url

    try:
        app.stop()
    except Exception:
        pass
    server_thread.kill()
    time.sleep(0.1)


def eventlet_wsgi_server(listener, wsgi_app):
    from eventlet import wsgi
    wsgi.server(listener, wsgi_app)
