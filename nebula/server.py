from typing import Dict, List, Callable, Optional, Any
from pathlib import Path
import mimetypes

from werkzeug.local import Local, LocalProxy
from werkzeug.wrappers import Request as WerkzeugRequest, Response as WerkzeugResponse
from werkzeug.serving import run_simple
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import NotFound, MethodNotAllowed
import socketio

from .utils.render_template import render_template
from .utils import init_static_serving , init_template_path , init_template_renderer

from .types import (
    AVAILABLE_METHODS,
    DEFAULT_TEMPLATES_DIR,
    DEFAULT_STATICS_DIR,
    DEFAULT_404_BODY,
    DEFAULT_500_BODY,
    DEFAULT_405_BODY,
)
from .exceptions import InvalidMethod, TemplateNotFound


_request_ctx_stack = Local()
current_request: WerkzeugRequest = LocalProxy(lambda: _request_ctx_stack.request)


class Nebula:
    def __init__(self, module_name: str, host: str, port: int, debug: bool = False):
        self.module_name = module_name
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

        self.jinja_env = None  # must be initialized via nebula.utils.init_template_renderer

        # Socket.IO initialization
        self.sio = socketio.Server(cors_allowed_origins="*", async_mode="eventlet")
        
        # Event handlers via decorators
        self._socketio_handlers = {}

    def init_all(self, static_endpoint: str = "static", static_dir: Optional[str] = None, template_dir: Optional[str] = None):
        static_serve_dir = self.statics_dir if not static_dir else static_dir
        init_static_serving(self, current_request, static_endpoint, static_serve_dir)

        template_loc = self.templates_dir if not template_dir else template_dir
        init_template_path(self, template_loc)

        init_template_renderer(self)

        return

    def run(self, host=None, port=None, debug=None, **kwargs):
        # Updating parameters if they're passed
        if host is None:
            host = self.host
        if port is None:
            port = self.port
        if debug is None:
            debug = self.debug

        # Creating WSGIApp middleware for handling Socket.IO requests
        app = socketio.WSGIApp(self.sio, self)

        # running with eventlet
        from eventlet import wsgi
        import eventlet
        
        listener = eventlet.listen((host, port))
        print(f"Starting Nebula server on http://{host}:{port}")
        wsgi.server(listener, app, log_output=debug)

    def dispatch_request(self, request: WerkzeugRequest):
        _request_ctx_stack.request = request
        with request:
            adapter = self.url_map.bind_to_environ(request.environ)
            try:
                endpoint, values = adapter.match()
                
                # Execute before_request hook
                if self.exec_before_request:
                    self.exec_before_request()
                
                response = self.view_functions[endpoint](**values)

                # Execute after_request hook
                if self.exec_after_request:
                    self.exec_after_request()
                
                if not isinstance(response, WerkzeugResponse):
                    # If the view function returns a string, wrap it in a Response object
                    response = WerkzeugResponse(str(response), 200)

                return response

            except NotFound:
                return self.error_handlers[404]()
            except MethodNotAllowed:
                return self.error_handlers[405]()
            except Exception as e:
                print(e)
                return self.error_handlers[500]()

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

    def add_url_rule(self, rule: str, endpoint: str = None, view_func: Callable = None, **options):
        """Adds URL rule for compatibility with Flask-SocketIO"""
        if endpoint is None:
            endpoint = view_func.__name__
        methods = options.get('methods', ['GET'])
        new_rule = Rule(rule, endpoint=endpoint, methods=methods)
        self.url_map.add(new_rule)
        if view_func:
            self.view_functions[endpoint] = view_func

    def before_request(self, func) -> Callable:
        self.exec_before_request = func
        return func

    def after_request(self, func) -> Callable:
        self.exec_after_request = func
        return func

    def internal_error_handler(self) -> WerkzeugResponse:
        return WerkzeugResponse(self.INTERNAL_ERROR, status=500)

    def method_not_allowed_handler(self) -> WerkzeugResponse:
        return WerkzeugResponse(self.METHOD_NOT_ALLOWED, status=405)

    def error_handler(self, http_code: int) -> Callable:
        if not (400 <= http_code <= 599):
            raise ValueError("Error handler must be 400-599 status code.")

        def decorator(func: Callable) -> Callable:
            self.error_handlers[http_code] = func
            return func 
        
        return decorator

    def content_not_found_handler(self) -> WerkzeugResponse:
        return WerkzeugResponse(self.NOT_FOUND, status=404)

    def render_template(self, filename: str, **kwargs) -> WerkzeugResponse:
        """Renders HTML template with use of Jinja2"""
        return render_template(self, filename, **kwargs)

    def on_event(self, event: str) -> Callable:
        """Decorator to register a WebSocket event handler."""
        def decorator(f: Callable) -> Callable:
            self.sio.on(event)(f)
            return f
        return decorator

    def on_connect(self) -> Callable:
        """Decorator to register a WebSocket connect handler."""
        def decorator(f: Callable) -> Callable:
            self.sio.on('connect')(f)
            return f
        return decorator

    def on_disconnect(self) -> Callable:
        """Decorator to register a WebSocket disconnect handler."""
        def decorator(f: Callable) -> Callable:
            self.sio.on('disconnect')(f)
            return f
        return decorator

    def emit(self, event: str, data: Any = None, to: str = None, broadcast: bool = False):
        """Sends event via WebSocket"""
        if broadcast:
            # Send to all connected clients
            self.sio.emit(event, data)
        elif to:
            # Send to one, selected client.
            self.sio.emit(event, data, to=to)
        else:
            # Send to sender 
            self.sio.emit(event, data)
