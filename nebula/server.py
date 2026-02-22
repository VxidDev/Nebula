from typing import Dict, List, Callable, Optional, Any
from pathlib import Path
import mimetypes

from werkzeug.wrappers import Request as WerkzeugRequest, Response as WerkzeugResponse
from werkzeug.serving import run_simple
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import NotFound, MethodNotAllowed

from .types import (
    AVAILABLE_METHODS,
    DEFAULT_TEMPLATES_DIR,
    DEFAULT_STATICS_DIR,
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

        self.url_map = Map()
        self.view_functions: Dict[str, Callable] = {}

        self.templates_dir = DEFAULT_TEMPLATES_DIR
        self.statics_dir = DEFAULT_STATICS_DIR

        self.NOT_FOUND = DEFAULT_404_BODY
        self.INTERNAL_ERROR = DEFAULT_500_BODY
        self.METHOD_NOT_ALLOWED = DEFAULT_405_BODY

        self.exec_before_request: Optional[Callable] = None
        self.exec_after_request: Optional[Callable] = None

        self.error_handlers: dict[int, Callable] = {
            404: self.content_not_found_handler,
            405: self.method_not_allowed_handler,
            500: self.internal_error_handler,
        }

    def run(self):
        run_simple(self.host, self.port, self, use_debugger=self.debug, use_reloader=self.debug)

    def dispatch_request(self, request: WerkzeugRequest):
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            
            # Execute before_request hook
            if self.exec_before_request:
                self.exec_before_request()

            response = self.view_functions[endpoint](request, **values)

            # Execute after_request hook
            if self.exec_after_request:
                self.exec_after_request()
            
            if not isinstance(response, WerkzeugResponse):
                # If the view function returns a string, wrap it in a Response object
                response = WerkzeugResponse(str(response), 200)

            return response

        except NotFound:
            return self.error_handlers[404](request)
        except MethodNotAllowed:
            return self.error_handlers[405](request)
        except Exception as e:
            print(e)
            return self.error_handlers[500](request)

    def __call__(self, environ, start_response):
        request = WerkzeugRequest(environ)

        with request:
            response = self.dispatch_request(request)
            return response(environ, start_response)

    def route(self, path: str, methods: List[str] = ["GET"]) -> Callable:
        def decorator(f):
            endpoint = f.__name__
            for method in methods:
                if method not in AVAILABLE_METHODS:
                    raise InvalidMethod(f"Method: '{method}' not recognized.")
            
            rule = Rule(path, endpoint=endpoint, methods=methods)
            self.url_map.add(rule)
            self.view_functions[endpoint] = f
            return f
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
        return func

    def after_request(self, func) -> Callable:
        self.exec_after_request = func
        return func

    def internal_error_handler(self, request) -> WerkzeugResponse:
        return WerkzeugResponse(self.INTERNAL_ERROR, status=500)

    def method_not_allowed_handler(self, request) -> WerkzeugResponse:
        return WerkzeugResponse(self.METHOD_NOT_ALLOWED, status=405)

    def error_handler(self, http_code: int) -> Callable:
        if not (400 <= http_code <= 599):
            raise ValueError("Error handler must be 400-599 status code.")

        def decorator(func: Callable) -> Callable:
            self.error_handlers[http_code] = func
            return func 
        
        return decorator

    def content_not_found_handler(self, request) -> WerkzeugResponse:
        return WerkzeugResponse(self.NOT_FOUND, status=404)
