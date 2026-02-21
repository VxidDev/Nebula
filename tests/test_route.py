import pytest
from nebula.utils.route import Route


def test_route_parsing():
    """
    Tests that the Route class correctly parses the path and query parameters.
    """
    route = Route("/test?param1=value1&param2=value2")
    assert route.path == "/test"
    assert route.query_params == {"param1": ["value1"], "param2": ["value2"]}


def test_route_no_query_params():
    """
    Tests that the Route class correctly handles paths with no query parameters.
    """
    route = Route("/test")
    assert route.path == "/test"
    assert route.query_params == {}


def test_route_root_path():
    """
    Tests that the Route class correctly handles the root path.
    """
    route = Route("/")
    assert route.path == "/"
    assert route.query_params == {}


def test_route_single_param():
    """
    Tests that the Route class correctly handles a single query parameter.
    """
    route = Route("/search?q=hello")
    assert route.path == "/search"
    assert route.query_params == {"q": ["hello"]}


def test_route_duplicate_params():
    """
    Tests that the Route class correctly handles duplicate query parameters.
    """
    route = Route("/filter?tag=python&tag=django")
    assert route.path == "/filter"
    assert route.query_params == {"tag": ["python", "django"]}


def test_route_empty_param_value():
    """
    Tests that the Route class correctly handles empty parameter values.
    """
    route = Route("/test?param=")
    assert route.path == "/test"
    assert route.query_params == {"param": [""]}


def test_route_param_without_value():
    """
    Tests that the Route class correctly handles parameters without values.
    """
    route = Route("/test?param")
    assert route.path == "/test"
    assert route.query_params == {"param": [""]}


def test_route_multiple_params_mixed():
    """
    Tests handling of multiple parameters with some empty values.
    """
    route = Route("/test?a=1&b=&c")
    assert route.path == "/test"
    assert route.query_params == {"a": ["1"], "b": [""], "c": [""]}


def test_route_special_characters_in_params():
    """
    Tests that the Route class correctly handles special characters in parameters.
    """
    route = Route("/test?name=hello%20world&symbol=%40")
    assert route.path == "/test"
    assert route.query_params == {"name": ["hello world"], "symbol": ["@"]}


def test_route_nested_path():
    """
    Tests that the Route class correctly handles nested paths.
    """
    route = Route("/api/v1/users/123")
    assert route.path == "/api/v1/users/123"
    assert route.query_params == {}


def test_route_path_with_extension():
    """
    Tests that the Route class correctly handles paths with file extensions.
    """
    route = Route("/static/style.css?v=1.0")
    assert route.path == "/static/style.css"
    assert route.query_params == {"v": ["1.0"]}
