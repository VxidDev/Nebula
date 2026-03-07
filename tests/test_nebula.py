import pytest
from werkzeug.wrappers import Response
from nebula.utils import jsonify
from nebula import TemplateNotFound
import os
import shutil
import tempfile
import ssl


def test_app_creation(app):
    assert app.host == "localhost"
    assert app.port == 8000
    assert not app.debug

def test_debug_mode():
    from nebula import Nebula
    app = Nebula(__name__, "localhost", 8000, debug=True)
    assert app.debug

def test_simple_route(app, client):
    @app.route("/test")
    def test():
        return "Hello, World!"

    response = client.get("/test")
    assert response.status_code == 200
    assert response.data == b"Hello, World!"

def test_post_route(app, client):
    @app.route("/test_post", methods=["POST"])
    def test_post():
        return "OK"

    response = client.post("/test_post")
    assert response.status_code == 200
    assert response.data == b"OK"

def test_not_found(client):
    response = client.get("/non_existent_route")
    assert response.status_code == 404
    assert b"<title>404 Not Found</title>" in response.data

def test_method_not_allowed(app, client):
    @app.route("/test_method")
    def test_method():
        return "OK"

    response = client.post("/test_method")
    assert response.status_code == 405
    assert b"<title>405 Method Not Allowed</title>" in response.data

def test_internal_server_error(app, client):
    @app.route("/error")
    def error():
        raise Exception("Test error")

    response = client.get("/error")
    assert response.status_code == 500
    assert b"<title>500 Internal Server Error</title>" in response.data

def test_custom_error_handler(app, client):
    @app.error_handler(404)
    def custom_not_found():
        return Response("Custom Not Found", status=404)

    response = client.get("/non_existent_route")
    assert response.status_code == 404
    assert response.data == b"Custom Not Found"

def test_jsonify():
    response = jsonify({"message": "Hello"})
    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert response.get_json() == {"message": "Hello"}

def test_jsonify_with_status_code():
    response = jsonify({"error": "Not Found"}, 404)
    assert response.status_code == 404
    assert response.get_json() == {"error": "Not Found"}

def test_before_request_hook(app, client):
    order = []

    @app.before_request
    def before_request_hook():
        order.append(1)

    @app.route("/hook")
    def hook():
        order.append(2)
        return "OK"

    client.get("/hook")
    assert order == [1, 2]

def test_after_request_hook(app, client):
    order = []

    @app.after_request
    def after_request_hook():
        order.append(3)

    @app.route("/hook_after")
    def hook_after():
        order.append(2)
        return "OK"
    
    # after_request is not called if the view function returns a Response object
    # so we need to call it manually
    @app.route("/hook_after_resp")
    def hook_after_resp():
        order.append(2)
        return Response("OK")


    client.get("/hook_after")
    assert order == [2, 3]

def test_template_rendering(app):
    temp_dir = tempfile.mkdtemp()
    app.templates_dir = temp_dir
    template_path = os.path.join(temp_dir, "test.html")
    with open(template_path, "w") as f:
        f.write("<h1>Hello, {{ name }}!</h1>")
    
    app.init_all()

    response = app.render_template("test.html", name="Nebula")
    assert response.status_code == 200
    assert b"<h1>Hello, Nebula!</h1>" in response.data

    shutil.rmtree(temp_dir)

from jinja2 import TemplateNotFound as JinjaTemplateNotFound

# ... (rest of the file) ...

def test_template_not_found(app):
    app.templates_dir = "non_existent_dir"
    app.init_all()
    with pytest.raises(JinjaTemplateNotFound):
        app.render_template("non_existent_template.html")

def test_static_files(app, client):
    temp_dir = tempfile.mkdtemp()
    app.statics_dir = temp_dir
    static_file_path = os.path.join(temp_dir, "style.css")
    with open(static_file_path, "w") as f:
        f.write("body { color: red; }")

    app.init_all()

    response = client.get("/static/style.css")
    assert response.status_code == 200
    assert response.data == b"body { color: red; }"
    assert response.mimetype == "text/css"

    shutil.rmtree(temp_dir)

from unittest.mock import patch

def test_https_server(app):
    @app.route("/")
    def index():
        return "Hello, HTTPS!"

    ssl_context = (
        os.path.join(os.path.dirname(__file__), "localhost+2.pem"), # should have a valid mkcert generated certificate!
        os.path.join(os.path.dirname(__file__), "localhost+2-key.pem") # should have a valid mkcert generated certificate!
    )
    
    with patch("eventlet.wsgi.server") as mock_wsgi_server:
        with patch("eventlet.wrap_ssl") as mock_wrap_ssl:
            app.run(host="localhost", port=8000, ssl_context=ssl_context)
            mock_wsgi_server.assert_called_once()
            mock_wrap_ssl.assert_called_once()
            args, kwargs = mock_wrap_ssl.call_args
            assert kwargs.get("certfile") == ssl_context[0]
            assert kwargs.get("keyfile") == ssl_context[1]

    app.stop()

def test_socketio_connect(socketio_server):
    # Unpack the fixture
    app, server_url = socketio_server
    import socketio
    
    sio_client = socketio.Client(request_timeout=10)

    @app.on_connect()
    def on_connect(sid, environ):
        pass # print(f"Socket.IO client connected: {sid}") # Removed print for cleaner output
    
    try:
        sio_client.connect(server_url, wait=True, wait_timeout=10)
        assert sio_client.connected
    finally:
        sio_client.disconnect()

def test_socketio_disconnect(socketio_server):
    # Unpack the fixture
    app, server_url = socketio_server
    import socketio

    sio_client = socketio.Client(request_timeout=10)

    @app.on_disconnect()
    def on_disconnect(sid):
        pass # print(f"Socket.IO client disconnected: {sid}") # Removed print for cleaner output

    try:
        sio_client.connect(server_url, wait=True, wait_timeout=10)
        sio_client.disconnect()
        assert not sio_client.connected
    finally:
        pass # Fixture will handle server teardown

def test_socketio_event(socketio_server):
    # Unpack the fixture
    app, server_url = socketio_server
    import socketio
    
    sio_client = socketio.Client(request_timeout=10)
    
    received_data = None

    @app.on_event("test_event")
    def on_test_event(sid, data):
        nonlocal received_data
        received_data = data
        
    try:
        sio_client.connect(server_url, wait=True, wait_timeout=10)
        sio_client.emit("test_event", {"data": "test"})
        sio_client.sleep(0.5)
        assert received_data == {"data": "test"}
    finally:
        sio_client.disconnect()

def test_socketio_emit(socketio_server):
    # Unpack the fixture
    app, server_url = socketio_server
    import socketio
    
    sio_client = socketio.Client(request_timeout=10)
    
    received_data = None
    
    @sio_client.on("response_event")
    def on_response(data):
        nonlocal received_data
        received_data = data

    @app.on_event("test_emit")
    def on_test_emit(sid, data):
        app.emit("response_event", {"data": "response"}, to=sid)

    try:
        sio_client.connect(server_url, wait=True, wait_timeout=10)
        sio_client.emit("test_emit", {"data": "test"})
        sio_client.sleep(0.5)
        assert received_data == {"data": "response"}
    finally:
        sio_client.disconnect()