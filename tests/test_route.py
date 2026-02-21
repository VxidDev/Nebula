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
