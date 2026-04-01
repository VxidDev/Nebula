from __future__ import annotations

import uvicorn
from typing import Dict, List, Callable, Optional, Any
from pathlib import Path
import mimetypes
import datetime
import ssl
import inspect
import os

import socketio

from .middleware import Middleware
from .request import Request
from .response import Response, PlainTextResponse, HTMLResponse, JSONResponse, RedirectResponse
from .routing import Route, RouteGroup
from .session import SecureCookieSessionManager, UserMixin, AnonymousUser
from .utils.render_template import ( 
    render_template, render_template_async, render_template_string, render_template_string_async 
)

from .utils import init_template_path, init_template_renderer, init_static_serving, init_template_renderer_sync

from .types import (
    AVAILABLE_METHODS,
    DEFAULT_TEMPLATES_DIR,
    DEFAULT_STATICS_DIR,
    DEFAULT_404_BODY,
    DEFAULT_500_BODY,
    DEFAULT_405_BODY,
)

from .exceptions import InvalidMethod, TemplateNotFound, DuplicateEndpoint, RouteNotFound, InvalidHTTPErrorCode, InvalidResponseClass, HTTPException
from contextvars import ContextVar

_current_request: ContextVar["Request"] = ContextVar("current_request")

def get_request() -> "Request":
    return _current_request.get()

class _RequestProxy:
    def __getattr__(self, item):
        try:
            return getattr(get_request(), item)
        except LookupError:
            raise RuntimeError(
                "No active request context. Use inside a request handler."
            )

def has_request() -> bool:
    try:
        _current_request.get()
        return True
    except LookupError:
        return False

request = _RequestProxy()

def handler_accepts_request(f):
    sig = inspect.signature(f)

    for name, param in sig.parameters.items():
        if name == "request":
            return True
        if param.annotation is Request:
            return True

    return False

def get_caller_file():
    frame = inspect.stack()[2]  # go up the stack
    module = inspect.getmodule(frame[0])

    if module and hasattr(module, "__file__"):
        return module.__file__

    return None

def is_valid_response_class(obj):
    try:
        return isinstance(obj, type) and issubclass(obj, Response)
    except TypeError:
        return False

def auto_detect_response(content, route):
    # JSON (strong signal)
    if isinstance(content, (dict, list)):
        return JSONResponse(content)

    # Explicit string handling
    if isinstance(content, str):
        stripped = content.lstrip()

        # HTML detection
        if stripped.startswith("<") and ">" in stripped:
            return HTMLResponse(content)

        # Redirect detection
        if stripped.startswith("http://") or stripped.startswith("https://"):
            return RedirectResponse(content)

        return PlainTextResponse(content)

    # Fallback for other types
    return PlainTextResponse(str(content))

class Nebula:
    def __init__(
        self, host: Optional[str] = "127.0.0.1",
        port: Optional[int] = 5000, debug: bool = False,
        import_string: Optional[str] = None, module_name: Optional[str] = None,
        middlewares: List[Middleware] = None
    ):
        self.module_name = module_name or get_caller_file()
        self.import_string = import_string
        self.debug = debug

        self.host = host
        self.port = port

        self.routes: List[Route] = []
        self._middlewares = middlewares or []

        self._static_routes: Dict[tuple, Route] = {}
        self._dynamic_routes: List[Route] = []
        self._path_methods: Dict[str, set] = {}

        self.templates_dir = DEFAULT_TEMPLATES_DIR
        self.statics_dir = DEFAULT_STATICS_DIR

        self.NOT_FOUND = DEFAULT_404_BODY
        self.INTERNAL_ERROR = DEFAULT_500_BODY
        self.METHOD_NOT_ALLOWED = DEFAULT_405_BODY


        # Default error handlers, async flag cached at registration time so
        # inspect.iscoroutinefunction() is never called on the hot path.
        self.error_handlers: dict[int, Callable] = {
            404: self.content_not_found_handler,
            405: self.method_not_allowed_handler,
            500: self.internal_error_handler,
        }
        self._error_handler_is_async: dict[int, bool] = {
            404: True,
            405: True,
            500: True,
        }

        self.jinja_env = None
        self.jinja_env_sync = None

        self.sio = socketio.AsyncServer(cors_allowed_origins="*", async_mode="asgi")

        self._core = self._build_core()
        self.app = socketio.ASGIApp(self.sio, other_asgi_app=self._core)

        self._socketio_handlers = {}

        self._session_manager: Optional[SecureCookieSessionManager] = None
        self._user_loader: Optional[Callable] = None
        self._user_loader_is_async: bool = False

    @staticmethod
    def _is_static_path(path_template: str) -> bool:
        """True when the path template contains no URL parameters."""
        return "{" not in path_template

    def _rebuild_route_index(self) -> None:
        """Rebuild lookup structures after a route is added.

        Cost is paid once at startup/registration time, not per request.
        """
        self._static_routes.clear()
        self._dynamic_routes.clear()
        self._path_methods.clear()

        for route in self.routes:
            pt = route.path_template
            m  = route.method.upper()

            self._path_methods.setdefault(pt, set()).add(m)

            if self._is_static_path(pt):
                self._static_routes[(pt, m)] = route
            else:
                self._dynamic_routes.append(route)

    def _build_core(self):
        async def app(scope, receive, send):
            if scope["type"] == "http":
                request = Request(scope, receive, send)
                token = _current_request.set(request)
                try:
                    return await self.handle_http(scope, receive, send)
                finally:
                    _current_request.reset(token)

            elif scope["type"] == "websocket":
                token = _current_request.set(None) 
                try:
                    return await self.app(scope, receive, send)
                finally:
                    _current_request.reset(token)

        return app

    def _build_middlewares(self, app: "ASGIApp") -> "ASGIApp":
        for mw in reversed(self._middlewares):
            app = mw.build(app)

        return app

    def setup_sessions(
        self,
        secret_key: str,
        cookie_name: str = "nebula_session",
        max_age: int = 86400,
        secure: bool = False,
    ) -> None:
        """Enable HMAC-signed cookie sessions."""
        self._session_manager = SecureCookieSessionManager(
            secret_key=secret_key,
            cookie_name=cookie_name,
            max_age=max_age,
            secure=secure,
        )

    def user_loader(self, func: Callable) -> Callable:
        """Register a callback that loads a user object from a stored ID."""
        self._user_loader = func
        self._user_loader_is_async = inspect.iscoroutinefunction(func)

        return func

    def init_all(
        self,
        static_endpoint: str = "static",
        static_dir: Optional[str] = None,
        template_dir: Optional[str] = None,
    ):
        init_static_serving(self, static_endpoint, static_dir or self.statics_dir)
        init_template_path(self, template_dir or self.templates_dir)
        init_template_renderer(self)
        init_template_renderer_sync(self)

    async def __call__(self, scope, receive, send):
        scope_type = scope["type"]

        if scope_type == "lifespan":
            return await self.handle_lifespan(receive, send)

        return await self.app(scope, receive, send)

    async def handle_lifespan(self, receive, send):
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                print("\033[1;36m[ STARTUP ]\033[1;0m")
                await send({"type": "lifespan.startup.complete"})

            elif message["type"] == "lifespan.shutdown":
                print("\033[1;36m[ SHUTDOWN ]\033[1;0m")
                await send({"type": "lifespan.shutdown.complete"})
                return

    async def handle_http(self, scope: dict, receive: callable, send: callable):
        request = get_request()

        session = None
        session_mgr = self._session_manager

        if session_mgr is not None:
            session = session_mgr.open_session(request)
            request.session = session

            user_loader = self._user_loader

            if user_loader is not None:
                uid = session.get(SecureCookieSessionManager._USER_ID_KEY)

                if uid is not None:
                    if self._user_loader_is_async:
                        loaded = await user_loader(uid)
                    else:
                        loaded = user_loader(uid)

                    request.user = loaded if loaded is not None else AnonymousUser()
                else:
                    request.user = AnonymousUser()
            else:
                request.user = AnonymousUser()

        path = request.path
        method = request.method
        route = None
        values: Dict[str, Any] = {}

        # O(1) static lookup, covers the vast majority of routes
        route = self._static_routes.get((path, method))

        if route is None:
            # Walk dynamic (parameterised) routes
            path_matched_wrong_method = False

            for r in self._dynamic_routes:
                m = r.match(path, method)

                if m is not None:
                    route = r
                    values = m
                    break

                if r.path_regex.match(path):
                    path_matched_wrong_method = True

            # Determine 404 vs 405 when no dynamic route handled it
            if route is None:
                if not path_matched_wrong_method:
                    # Check static routes for wrong-method 405 detection
                    for (pt, _), r in self._static_routes.items():
                        if r.path_regex.match(path):
                            path_matched_wrong_method = True
                            break

                if path_matched_wrong_method:
                    return await self._dispatch_error(405, scope, receive, send)

                return await self._dispatch_error(404, scope, receive, send)
        
        # Middleware application for the route handler
        async def call_handler(inner_scope, inner_receive, inner_send):
            # The actual route handler execution
            if route.is_async:
                if route.accepts_request_arg:
                    response_content = await route.handler(request, **values)
                else:
                    response_content = await route.handler(**values)
            else:
                if route.accepts_request_arg:
                    response_content = route.handler(request, **values)
                else:
                    response_content = route.handler(**values)

            # Wrap bare return values into Response objects
            if isinstance(response_content, Response):
                response = response_content
            elif route.return_class:
                if isinstance(response_content, Response):
                    response = response_content
                else:
                    response = route.return_class(response_content)
            else:
                response = auto_detect_response(response_content, route)

            # Persist session if dirty
            if session is not None and session.modified:
                session_mgr.save_session(session, response)
            
            await response(inner_scope, inner_receive, inner_send)

        current_app = call_handler
        # Apply global middlewares first, then route-specific middlewares
        # Middlewares are applied in reverse order of how they should execute (outermost first)
        all_middlewares = self._middlewares + route.middlewares
        for mw in reversed(all_middlewares):
            current_app = mw.build(current_app)

        try:
            return await current_app(scope, receive, send)

        except Exception as e:
            error = str(e)
            print(f"\033[1;31mERROR:\033[1;0m {error if len(error) > 0 else 'No description provided.'}")

            if isinstance(e, HTTPException):
                status_code = e.status_code
            else:
                status_code = 500

            return await self._dispatch_error(status_code, scope, receive, send)

    async def _dispatch_error(self, code: int, scope, receive, send):
        handler = self.error_handlers[code]

        if not handler:
            handler = self.error_handlers[500]

        if self._error_handler_is_async.get(code, True):
            return await handler(scope, receive, send)

        return handler(scope, receive, send)

    def route(self, path: str, methods: List[str] = None, return_class = None, group_middlewares: List[Middleware] | None = None, route_middlewares: List[Middleware] | None = None) -> Callable:
        def decorator(f: Callable) -> Callable:
            mds = methods or ["GET"]
            is_async = inspect.iscoroutinefunction(f)

            # Check if the handler accepts request
            accepts_request = handler_accepts_request(f)

            for method in mds:
                if method not in AVAILABLE_METHODS:
                    raise InvalidMethod(f"Method: '{method}' not recognized.")

                for existing_route in self.routes:
                    if existing_route.path_template == path and existing_route.method == method.upper():
                        raise DuplicateEndpoint(f"Route '{path}' with method '{method}' already exists.")

                sig = inspect.signature(f)
                annotation = None if sig.return_annotation is inspect._empty else sig.return_annotation 
                final_return = return_class if return_class is not None else annotation

                if not is_valid_response_class(final_return) and final_return is not None:
                    name = getattr(final_return, "__name__", str(final_return))

                    obj_name = "Class" if isinstance(final_return, type) else "Type"

                    raise InvalidResponseClass(
                        f"{obj_name}: {name} does not inherit from Response class."
                    )

                new_route = Route(path, method, f, final_return)
                new_route.is_async = is_async # cache async flag on the Route object
                new_route.accepts_request_arg = accepts_request

                # Assign middlewares
                new_route.middlewares = (group_middlewares or []) + (route_middlewares or [])

                self.routes.append(new_route)

            self._rebuild_route_index()
            return f

        return decorator

    def get(self, path: str, return_class = None) -> Callable:
        return self.route(path, ["GET"], return_class)
    
    def post(self, path: str, return_class = None) -> Callable:
        return self.route(path, ["POST"], return_class)

    def put(self, path: str, return_class = None) -> Callable:
        return self.route(path, ["PUT"], return_class)

    def delete(self, path: str, return_class = None) -> Callable:
        return self.route(path, ["DELETE"], return_class)

    def add_url_rule(
        self, rule: str, endpoint: str = None, view_func: Callable = None, return_class = None, **options
    ):
        methods = options.get("methods", ["GET"])

        if view_func:
            is_async = inspect.iscoroutinefunction(view_func)

            for method in methods:
                if method not in AVAILABLE_METHODS:
                    raise InvalidMethod(f"Method: '{method}' not recognized.")

                for existing_route in self.routes:
                    if existing_route.path_template == rule and existing_route.method == method.upper():
                        raise DuplicateEndpoint(f"Route '{rule}' with method '{method}' already exists.")

                if return_class is not None and not is_valid_response_class(return_class):
                    raise InvalidResponseClass(
                        f"Class: {return_class.__name__} does not inherit from Response class."
                    )

                new_route = Route(rule, method, view_func, return_class)
                new_route.is_async = is_async

                self.routes.append(new_route)

            self._rebuild_route_index()

    async def internal_error_handler(self, scope: dict, receive: Callable, send: Callable): # basic handler for HTTP 500
        response = HTMLResponse(self.INTERNAL_ERROR, status_code=500)
        await response(scope, receive, send)

    async def method_not_allowed_handler(self, scope: dict, receive: Callable, send: Callable): # basic handler for HTTP 405
        response = HTMLResponse(self.METHOD_NOT_ALLOWED, status_code=405)
        await response(scope, receive, send)

    async def content_not_found_handler(self, scope: dict, receive: Callable, send: Callable): # basic handler for HTTP 404
        response = HTMLResponse(self.NOT_FOUND, status_code=404)
        await response(scope, receive, send)

    def error_handler(self, http_code: int):
        if not (400 <= http_code <= 599):
            raise InvalidHTTPErrorCode(
                f"HTTP code {http_code} is not a valid error code (must be 400 - 599)"
            )

        def wrapper(func: Callable):
            self.error_handlers[http_code] = func
            self._error_handler_is_async[http_code] = inspect.iscoroutinefunction(func)

            return func

        return wrapper

    async def render_template_async(self, filename: str, **kwargs) -> HTMLResponse:
        return await render_template_async(self, filename, **kwargs)

    def render_template(self, filename: str, **kwargs) -> HTMLResponse:
        return render_template(self, filename, **kwargs)

    async def render_template_string_async(self, template_string: str, **kwargs) -> HTMLResponse:
        return await render_template_string_async(self, template_string, **kwargs)

    def render_template_string(self, template_string: str, **kwargs) -> HTMLResponse:
        return render_template_string(self, template_string, **kwargs)

    def on_event(self, event: str) -> Callable:
        def decorator(f: Callable) -> Callable:
            self.sio.on(event)(f)
            return f

        return decorator

    def on_connect(self) -> Callable:
        def decorator(f: Callable) -> Callable:
            self.sio.on("connect")(f)
            return f

        return decorator

    def on_disconnect(self) -> Callable:
        def decorator(f: Callable) -> Callable:
            self.sio.on("disconnect")(f)
            return f

        return decorator

    async def emit(
        self,
        event: str,
        data: Any = None,
        to: str = None,
        broadcast: bool = False,
    ):
        if broadcast or to is None:
            await self.sio.emit(event, data)
        else:
            await self.sio.emit(event, data, to=to)

    def set_import_string(self, string: str):
        self.import_string = string

    def group(self, prefix: str, middlewares: list[Middleware] | None = None) -> RouteGroup:
        return RouteGroup(self, prefix, middlewares)

    def run(self, host: Optional[str] = None , port: Optional[str] = None):
        run_dev(self, host, port)

def run_dev(app: Nebula, host: Optional[str] = None, port: Optional[str] = None, **kwargs):
    uvicorn.run(app, host=host or app.host, port=port or app.port, **kwargs)

def run_prod(
    app: Nebula,
    host: Optional[str] = None,
    port: Optional[int] = None,
    workers: int = 1,
    log_level: str = "info",
    **kwargs
) -> None:
    if not app.import_string:
        raise RuntimeError(
            "Import string required for production. "
            "Call: app.set_import_string('app') # 'app' is Nebula instance's name."
        )

    if workers < 1:
        raise ValueError("workers must be >= 1")

    # Resolve module path safely
    module_path = Path(app.module_name).resolve()
    if not module_path.exists():
        raise FileNotFoundError(f"Module not found: {module_path}")

    if module_path.suffix != ".py":
        raise ValueError(f"Expected a .py file, got: {module_path}")

    directory = str(module_path.parent)
    module_name = module_path.stem

    # Build ASGI app path
    app_path = f"{module_name}:{app.import_string}"

    uvicorn.run(
        app_path,
        host=host or app.host,
        port=port or app.port,
        workers=workers,
        app_dir=directory,
        reload=False, 
        log_level=log_level,
        **kwargs
    )