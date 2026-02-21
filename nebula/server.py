from http.server import ThreadingHTTPServer
from typing import Dict, List, Callable, Optional, Any

from .core import Response, Request
from .handlers import RequestHandler
from .types import (
    AVAILABLE_METHODS,
    DEFAULT_TEMPLATES_DIR,
    DEFAULT_404_BODY,
    DEFAULT_500_BODY,
    DEFAULT_405_BODY,
)
from .exceptions import InvalidMethod, TemplateNotFound


class Nebula:
    def __init__(self, host: str, port: int, debug: bool = False):
        self.debug = debug

        self.host = host
        self.port = port

        self.routes: Dict[str, Dict[str, Any]] = {}
        self.templates_dir = DEFAULT_TEMPLATES_DIR

        self.NOT_FOUND = DEFAULT_404_BODY
        self.INTERNAL_ERROR = DEFAULT_500_BODY
        self.METHOD_NOT_ALLOWED = DEFAULT_405_BODY

        self.exec_before_request: Optional[Callable] = None
        self.exec_after_request: Optional[Callable] = None
        self.exec_on_internal_error: Callable = self.internal_error_handler
        self.exec_on_method_not_allowed: Callable = self.method_not_allowed_handler

        self.request: Optional[Request] = None

        RequestHandler.server_instance = self
        self.handler = RequestHandler
        self.server = ThreadingHTTPServer((self.host, self.port), self.handler)

    def run(self) -> None:
        try:
            print(f"Server is up! - http://{self.host}:{self.port}")
            self.server.serve_forever()
        except KeyboardInterrupt:
            self.server.shutdown()

    def route(self, path: str, methods: List[str] = ["GET"]) -> Callable:
        def decorator(func):
            for method in methods:
                if method not in AVAILABLE_METHODS:
                    raise InvalidMethod(f"Method: '{method}' not recognized.")

            self.routes[path] = {"function": func, "methods": methods}
            return func

        return decorator

    def load_template(self, filename: str) -> str:
        """
        Open and read file from ./templates/<filepath>
        """

        try:
            with open(f"{self.templates_dir}/{filename}", "r") as file:
                content = file.read()
            return content
        except FileNotFoundError:
            raise TemplateNotFound(f"File: '{filename}' not found in {self.templates_dir} directory.")

    def before_request(self, func) -> Callable:
        self.exec_before_request = func

        def wrapper():
            return func

        return wrapper

    def after_request(self, func) -> Callable:
        self.exec_after_request = func

        def wrapper():
            return func

        return wrapper

    def internal_error_handler(self, func=None) -> Response:
        if func:
            self.exec_on_internal_error = func

        return Response(self.INTERNAL_ERROR, 500)

    def method_not_allowed_handler(self, func=None) -> Response:
        if func:
            self.exec_on_method_not_allowed = func

        return Response(self.METHOD_NOT_ALLOWED, 405)
