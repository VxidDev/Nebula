import pytest
import os
import tempfile
import shutil
from nebula import Nebula, TemplateNotFound, InvalidMethod
from nebula.utils import jsonify
from werkzeug.wrappers import Response
from werkzeug.test import Client

class TestNebulaInit:
    """Tests for Nebula initialization."""

    def test_nebula_init_default(self):
        """Tests Nebula initialization with default values."""
        app = Nebula("localhost", 8000)
        assert app.host == "localhost"
        assert app.port == 8000
        assert app.debug is False
        assert len(list(app.url_map.iter_rules())) == 0
        assert app.templates_dir == "./templates"

    def test_nebula_init_debug(self):
        """Tests Nebula initialization with debug mode."""
        app = Nebula("localhost", 8000, debug=True)
        assert app.debug is True

    def test_nebula_init_custom_host_port(self):
        """Tests Nebula initialization with custom host and port."""
        app = Nebula("127.0.0.1", 5000)
        assert app.host == "127.0.0.1"
        assert app.port == 5000


class TestNebulaRoute:
    """Tests for Nebula route decorator."""

    def test_route_decorator_get(self):
        """Tests route decorator with GET method."""
        app = Nebula("localhost", 8000)

        @app.route("/test")
        def test_handler(request):
            return Response("OK", 200)

        rules = list(app.url_map.iter_rules())
        assert len(rules) == 1
        assert rules[0].rule == "/test"
        assert "GET" in rules[0].methods
        assert rules[0].endpoint == "test_handler"

    def test_route_decorator_post(self):
        """Tests route decorator with POST method."""
        app = Nebula("localhost", 8000)

        @app.route("/api/data", methods=["POST"])
        def data_handler(request):
            return Response("Created", 201)

        rules = list(app.url_map.iter_rules())
        assert len(rules) == 1
        assert "POST" in rules[0].methods

    def test_route_decorator_multiple_methods(self):
        """Tests route decorator with multiple methods."""
        app = Nebula("localhost", 8000)

        @app.route("/api/resource", methods=["GET", "POST"])
        def resource_handler(request):
            return Response("OK", 200)

        rules = list(app.url_map.iter_rules())
        assert len(rules) == 1
        assert "GET" in rules[0].methods
        assert "POST" in rules[0].methods

    def test_route_decorator_invalid_method(self):
        """Tests route decorator raises error for invalid method."""
        app = Nebula("localhost", 8000)

        with pytest.raises(InvalidMethod):
            @app.route("/test", methods=["INVALID"])
            def test_handler(request):
                return Response("OK", 200)

    def test_route_decorator_multiple_routes(self):
        """Tests multiple routes on same app."""
        app = Nebula("localhost", 8000)

        @app.route("/route1")
        def handler1(request):
            return Response("1", 200)

        @app.route("/route2")
        def handler2(request):
            return Response("2", 200)

        rules = list(app.url_map.iter_rules())
        assert len(rules) == 2


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

    def test_load_template_not_found(self):
        """Tests template not found exception."""
        app = Nebula("localhost", 8000)
        app.templates_dir = self.temp_dir

        with pytest.raises(TemplateNotFound):
            app.load_template("nonexistent.html")

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


class TestNebulaHooks:
    """Tests for Nebula request hooks."""

    def test_internal_error_handler(self):
        """Tests internal_error_handler."""
        app = Nebula("localhost", 8000)

        @app.error_handler(500)
        def custom_error(request):
            return Response("Custom Error", 500)

        assert 500 in app.error_handlers

    def test_method_not_allowed_handler(self):
        """Tests method_not_allowed_handler."""
        app = Nebula("localhost", 8000)

        @app.error_handler(405)
        def custom_method_not_allowed(request):
            return Response("Method Not Allowed", 405)

        assert 405 in app.error_handlers


class TestJsonify:
    """Tests for jsonify helper function."""

    def test_jsonify_basic(self):
        """Tests jsonify with basic dictionary."""
        response = jsonify({"key": "value"})
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"
        import json
        assert json.loads(response.data) == {"key": "value"}

    def test_jsonify_custom_status(self):
        """Tests jsonify with custom status code."""
        response = jsonify({"error": "not found"}, status=404)
        assert response.status_code == 404

    def test_jsonify_nested_dict(self):
        """Tests jsonify with nested dictionary."""
        data = {"user": {"name": "John", "details": {"age": 30}}}
        response = jsonify(data)
        import json
        assert json.loads(response.data) == data

    def test_jsonify_list(self):
        """Tests jsonify with list."""
        data = [1, 2, 3, 4, 5]
        response = jsonify(data)
        import json
        assert json.loads(response.data) == data

    def test_jsonify_empty_dict(self):
        """Tests jsonify with empty dictionary."""
        response = jsonify({})
        import json
        assert json.loads(response.data) == {}
