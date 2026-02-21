import json
import pytest
from nebula.core import Data, Request, Response
from nebula.utils.route import Route


class TestData:
    """Tests for the Data class."""

    def test_data_empty(self):
        """Tests that Data handles empty initialization."""
        data = Data(None)
        assert data.raw == b""
        assert data.get_json() == {}
        assert data.text() == ""
        assert data.bytes() == b""

    def test_data_from_bytes(self):
        """Tests that Data correctly stores raw bytes."""
        raw = b"hello world"
        data = Data(raw)
        assert data.raw == raw
        assert data.bytes() == raw

    def test_data_text(self):
        """Tests that Data.text() correctly decodes bytes to string."""
        raw = b"hello world"
        data = Data(raw)
        assert data.text() == "hello world"

    def test_data_text_utf8(self):
        """Tests that Data.text() correctly handles UTF-8 encoding."""
        raw = "Привет мир".encode("utf-8")
        data = Data(raw)
        assert data.text() == "Привет мир"

    def test_data_get_json(self):
        """Tests that Data.get_json() correctly parses JSON."""
        raw = json.dumps({"key": "value", "number": 42}).encode("utf-8")
        data = Data(raw)
        assert data.get_json() == {"key": "value", "number": 42}

    def test_data_get_json_empty(self):
        """Tests that Data.get_json() returns empty dict for empty data."""
        data = Data(None)
        assert data.get_json() == {}

    def test_data_get_json_list(self):
        """Tests that Data.get_json() handles JSON arrays."""
        raw = json.dumps([1, 2, 3]).encode("utf-8")
        data = Data(raw)
        assert data.get_json() == [1, 2, 3]

    def test_data_get_json_nested(self):
        """Tests that Data.get_json() handles nested JSON."""
        raw = json.dumps({"user": {"name": "John", "age": 30}}).encode("utf-8")
        data = Data(raw)
        assert data.get_json() == {"user": {"name": "John", "age": 30}}

    def test_data_invalid_json(self):
        """Tests that Data.get_json() raises error for invalid JSON."""
        raw = b"not valid json"
        data = Data(raw)
        with pytest.raises(json.JSONDecodeError):
            data.get_json()


class TestResponse:
    """Tests for the Response class."""

    def test_response_basic(self):
        """Tests basic Response initialization."""
        response = Response(body="Hello", http_code=200)
        assert response.body == "Hello"
        assert response.http_code == 200
        assert response.headers == {}

    def test_response_with_headers(self):
        """Tests Response with custom headers."""
        headers = {"Content-Type": "text/html", "X-Custom": "value"}
        response = Response(body="Hello", http_code=200, headers=headers)
        assert response.headers == headers

    def test_response_html(self):
        """Tests Response for HTML content."""
        html = "<html><body>Hello</body></html>"
        response = Response(body=html, http_code=200, headers={"Content-Type": "text/html"})
        assert response.body == html
        assert response.headers["Content-Type"] == "text/html"

    def test_response_json(self):
        """Tests Response for JSON content."""
        response = Response(
            body=json.dumps({"status": "ok"}),
            http_code=200,
            headers={"Content-Type": "application/json"},
        )
        assert json.loads(response.body) == {"status": "ok"}

    def test_response_error_codes(self):
        """Tests Response with various error codes."""
        for code in [400, 401, 403, 404, 500, 502, 503]:
            response = Response(body=f"Error {code}", http_code=code)
            assert response.http_code == code

    def test_response_empty_body(self):
        """Tests Response with empty body."""
        response = Response(body="", http_code=204)
        assert response.body == ""
        assert response.http_code == 204


class TestRequest:
    """Tests for the Request class."""

    def test_request_basic(self):
        """Tests basic Request initialization."""
        route = Route("/test")
        request = Request(route=route, method="GET", data=None)
        assert request.route.path == "/test"
        assert request.method == "GET"
        assert request.data is None

    def test_request_with_data(self):
        """Tests Request with Data object."""
        route = Route("/api/data")
        data = Data(b'{"key": "value"}')
        request = Request(route=route, method="POST", data=data)
        assert request.route.path == "/api/data"
        assert request.method == "POST"
        assert request.data is not None
        assert request.data.get_json() == {"key": "value"}

    def test_request_methods(self):
        """Tests Request with different HTTP methods."""
        route = Route("/test")
        for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
            request = Request(route=route, method=method, data=None)
            assert request.method == method

    def test_request_query_params(self):
        """Tests that Request has access to query params through route."""
        route = Route("/search?q=hello&page=1")
        request = Request(route=route, method="GET", data=None)
        assert request.route.query_params == {"q": ["hello"], "page": ["1"]}
