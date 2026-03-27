class InvalidMethod(Exception):
    """Raised when an invalid HTTP method is used."""
    pass

class TemplateNotFound(Exception):
    """Raised when a template file is not found."""
    pass

class DuplicateEndpoint(Exception):
    """Raised when an attempt is made to register a duplicate endpoint."""
    pass

class RouteNotFound(Exception):
    """Raised when a requested route is not found."""
    pass

class InvalidHTTPErrorCode(Exception):
    """Raised when an HTTP status code is expected to be an error (400-599) but isn't."""
    pass
