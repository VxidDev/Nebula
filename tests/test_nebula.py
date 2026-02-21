import pytest
import os
import tempfile
import shutil
from nebula import Nebula, Response, jsonify, TemplateNotFound, InvalidMethod


class TestNebulaInit:
    """Tests for Nebula initialization."""

    def test_nebula_init_default(self):
        """Tests Nebula initialization with default values."""
        app = Nebula("localhost", 8000)
        assert app.host == "localhost"
        assert app.port == 8000
        assert app.debug is False
        assert app.routes == {}
        assert app.templates_dir == "./templates"

        app.stop()

    def test_nebula_init_debug(self):
        """Tests Nebula initialization with debug mode."""
        app = Nebula("localhost", 8000, debug=True)
        assert app.debug is True

        app.stop()

    def test_nebula_init_custom_host_port(self):
        """Tests Nebula initialization with custom host and port."""
        app = Nebula("127.0.0.1", 5000)
        assert app.host == "127.0.0.1"
        assert app.port == 5000

        app.stop()


class TestNebulaRoute:
    """Tests for Nebula route decorator."""

    def test_route_decorator_get(self):
        """Tests route decorator with GET method."""
        app = Nebula("localhost", 8000)

        @app.route("/test")
        def test_handler():
            return Response("OK", 200)

        assert "/test" in app.routes
        assert app.routes["/test"]["function"] == test_handler
        assert "GET" in app.routes["/test"]["methods"]

        app.stop()

    def test_route_decorator_post(self):
        """Tests route decorator with POST method."""
        app = Nebula("localhost", 8000)

        @app.route("/api/data", methods=["POST"])
        def data_handler():
            return Response("Created", 201)

        assert "/api/data" in app.routes
        assert "POST" in app.routes["/api/data"]["methods"]

        app.stop()

    def test_route_decorator_multiple_methods(self):
        """Tests route decorator with multiple methods."""
        app = Nebula("localhost", 8000)

        @app.route("/api/resource", methods=["GET", "POST"])
        def resource_handler():
            return Response("OK", 200)

        assert "/api/resource" in app.routes
        assert "GET" in app.routes["/api/resource"]["methods"]
        assert "POST" in app.routes["/api/resource"]["methods"]

        app.stop()

    def test_route_decorator_invalid_method(self):
        """Tests route decorator raises error for invalid method."""
        app = Nebula("localhost", 8000)

        with pytest.raises(InvalidMethod):

            @app.route("/test", methods=["INVALID"])
            def test_handler():
                return Response("OK", 200)

        app.stop()

    def test_route_decorator_multiple_routes(self):
        """Tests multiple routes on same app."""
        app = Nebula("localhost", 8000)

        @app.route("/route1")
        def handler1():
            return Response("1", 200)

        @app.route("/route2")
        def handler2():
            return Response("2", 200)

        assert len(app.routes) == 2
        assert "/route1" in app.routes
        assert "/route2" in app.routes

        app.stop()


class TestNebulaTemplates:
    """Tests for Nebula template loading."""

    def setup_method(self):
        """Create temporary templates directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_templates_dir = "./templates"

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_template_success(self):
        """Tests successful template loading."""
        app = Nebula("localhost", 8000)
        app.templates_dir = self.temp_dir

        template_path = os.path.join(self.temp_dir, "test.html")
        with open(template_path, "w") as f:
            f.write("<h1>Hello</h1>")

        content = app.load_template("test.html")
        assert content == "<h1>Hello</h1>"

        app.stop()

    def test_load_template_not_found(self):
        """Tests template not found exception."""
        app = Nebula("localhost", 8000)
        app.templates_dir = self.temp_dir

        with pytest.raises(TemplateNotFound):
            app.load_template("nonexistent.html")

        app.stop()

    def test_load_template_nested_path(self):
        """Tests loading template from nested directory."""
        app = Nebula("localhost", 8000)
        app.templates_dir = self.temp_dir

        nested_dir = os.path.join(self.temp_dir, "pages")
        os.makedirs(nested_dir)
        template_path = os.path.join(nested_dir, "home.html")
        with open(template_path, "w") as f:
            f.write("<h1>Home</h1>")

        content = app.load_template("pages/home.html")
        assert "<h1>Home</h1>" in content

        app.stop()


class TestNebulaHooks:
    """Tests for Nebula request hooks."""

    def test_before_request(self):
        """Tests before_request hook."""
        app = Nebula("localhost", 8000)
        executed = {"value": False}

        @app.before_request
        def hook(request):
            executed["value"] = True

        assert app.exec_before_request is not None

        app.stop()

    def test_after_request(self):
        """Tests after_request hook."""
        app = Nebula("localhost", 8000)
        executed = {"value": False}

        @app.after_request
        def hook(request):
            executed["value"] = True

        assert app.exec_after_request is not None

        app.stop()

    def test_internal_error_handler(self):
        """Tests internal_error_handler."""
        app = Nebula("localhost", 8000)

        @app.internal_error_handler
        def custom_error():
            return Response("Custom Error", 500)

        assert app.exec_on_internal_error is not None

        app.stop()

    def test_method_not_allowed_handler(self):
        """Tests method_not_allowed_handler."""
        app = Nebula("localhost", 8000)

        @app.method_not_allowed_handler
        def custom_method_not_allowed():
            return Response("Method Not Allowed", 405)

        assert app.exec_on_method_not_allowed is not None

        app.stop()


class TestJsonify:
    """Tests for jsonify helper function."""

    def test_jsonify_basic(self):
        """Tests jsonify with basic dictionary."""
        response = jsonify({"key": "value"})
        assert response.http_code == 200
        assert response.headers["Content-Type"] == "application/json"
        import json
        assert json.loads(response.body) == {"key": "value"}

    def test_jsonify_custom_status(self):
        """Tests jsonify with custom status code."""
        response = jsonify({"error": "not found"}, status=404)
        assert response.http_code == 404

    def test_jsonify_nested_dict(self):
        """Tests jsonify with nested dictionary."""
        data = {"user": {"name": "John", "details": {"age": 30}}}
        response = jsonify(data)
        import json
        assert json.loads(response.body) == data

    def test_jsonify_list(self):
        """Tests jsonify with list."""
        data = [1, 2, 3, 4, 5]
        response = jsonify(data)
        import json
        assert json.loads(response.body) == data

    def test_jsonify_empty_dict(self):
        """Tests jsonify with empty dictionary."""
        response = jsonify({})
        import json
        assert json.loads(response.body) == {}
