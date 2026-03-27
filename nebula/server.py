import uvicorn
from typing import Dict, List, Callable, Optional, Any
from pathlib import Path
import mimetypes
import datetime
import ssl
import inspect

import socketio

from .request import Request
from .response import Response, PlainTextResponse, HTMLResponse
from .routing import Route
from .session import SecureCookieSessionManager, UserMixin, AnonymousUser
from .utils.render_template import render_template
from .utils import init_template_path, init_template_renderer, init_static_serving

from .types import (
    AVAILABLE_METHODS,
    DEFAULT_TEMPLATES_DIR,
    DEFAULT_STATICS_DIR,
    DEFAULT_404_BODY,
    DEFAULT_500_BODY,
    DEFAULT_405_BODY,
)
from .exceptions import InvalidMethod, TemplateNotFound, DuplicateEndpoint, RouteNotFound, InvalidHTTPErrorCode


class Nebula:
    def __init__(self, module_name: str, host: str, port: int, debug: bool = False):
        self.module_name = module_name
        self.debug = debug

        self.host = host
        self.port = port

        self.routes: List[Route] = []

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

        self.sio = socketio.AsyncServer(cors_allowed_origins="*", async_mode="asgi")

        self.app = socketio.ASGIApp(
            self.sio,
            other_asgi_app=self.handle_http  # fallback HTTP handler
        )

        self._socketio_handlers = {}

        # Session management
        self._session_manager: Optional[SecureCookieSessionManager] = None
        self._user_loader: Optional[Callable] = None

    def setup_sessions(
        self,
        secret_key: str,
        cookie_name: str = "nebula_session",
        max_age: int = 86400,
        secure: bool = False,
    ) -> None:
        """Enable HMAC-signed cookie sessions.

        Call this before running the server.

        Args:
            secret_key: Key used to sign session cookies.
            cookie_name: Cookie name (default: nebula_session).
            max_age: Cookie lifetime in seconds (default: 86400 = 1 day).
            secure: Set the Secure flag - use True with HTTPS only.
        """
        self._session_manager = SecureCookieSessionManager(
            secret_key=secret_key,
            cookie_name=cookie_name,
            max_age=max_age,
            secure=secure,
        )

    def user_loader(self, func: Callable) -> Callable:
        """Register a callback that loads a user object from a stored ID.

        The function receives the user ID string from the session and should
        return the user object, or None if the user no longer exists.
        """
        self._user_loader = func
        return func

    def init_all(
        self,
        static_endpoint: str = "static",
        static_dir: Optional[str] = None,
        template_dir: Optional[str] = None,
    ):
        static_serve_dir = self.statics_dir if not static_dir else static_dir
        init_static_serving(self, static_endpoint, static_serve_dir)

        template_loc = self.templates_dir if not template_dir else template_dir
        init_template_path(self, template_loc)

        init_template_renderer(self)

        return

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            await self.handle_lifespan(receive, send)
        else:
            await self.app(scope, receive, send)

    async def handle_lifespan(self, receive, send):
        while True:
            message = await receive()

            if message["type"] == "lifespan.startup":
                print("[Nebula] Startup")
                await send({"type": "lifespan.startup.complete"})

            elif message["type"] == "lifespan.shutdown":
                print("[Nebula] Shutdown")
                await send({"type": "lifespan.shutdown.complete"})
                return

    async def handle_http(self, scope: dict, receive: Callable, send: Callable):
        request = Request(scope, receive, send)

        session = None
        user = AnonymousUser()

        if self._session_manager:
            session = self._session_manager.open_session(request)
            request.session = session # Make session available on request object

            if self._user_loader and SecureCookieSessionManager._USER_ID_KEY in session:
                loaded = await self._user_loader(session[SecureCookieSessionManager._USER_ID_KEY])
                if loaded is not None:
                    user = loaded
            request.user = user # Make user available on request object


        path = request.path
        method = request.method

        # Find matching route
        match_found = False
        method_allowed = False
        response = None
        for route in self.routes:
            values = route.match(path, method)
            if values is not None:
                match_found = True
                method_allowed = True
                try:
                    # Call before_request if defined
                    if self.exec_before_request:
                        if inspect.iscoroutinefunction(self.exec_before_request):
                            await self.exec_before_request(request)
                        else:
                            self.exec_before_request(request)

                    if inspect.iscoroutinefunction(route.handler):
                        response_content = await route.handler(request, **values)
                    else:
                        response_content = route.handler(request, **values)

                    # Call after_request if defined
                    if self.exec_after_request:
                        if inspect.iscoroutinefunction(self.exec_after_request):
                            await self.exec_after_request(request)
                        else:
                            self.exec_after_request(request)

                    if not isinstance(response_content, Response):
                        response = PlainTextResponse(str(response_content))
                    else:
                        response = response_content

                    break # Exit loop once route is handled
                except Exception as e:
                    print(f"Error handling request: {e}")

                    if inspect.iscoroutinefunction(self.error_handlers[500]):
                        response = await self.error_handlers[500](scope, receive, send)
                    else:
                        response = self.error_handlers[500](score, receive, send)

                    return response
            elif route.path_regex.match(path):
                match_found = True
                # A route matches the path, but not the method

        if response is None: # No route handled the request successfully
            if not match_found:
                if inspect.iscoroutinefunction(self.error_handlers[404]):
                    response = await self.error_handlers[404](scope, receive, send)
                else:
                    response = self.error_handlers[404](scope, receive, send)

                return response
            elif match_found and not method_allowed:
                if inspect.iscoroutinefunction(self.error_handlers[405]):
                    response = await self.error_handlers[405](scope, receive, send)
                else:
                    response = self.error_handlers[405](scope, receive, send)

                return response

        # Save session to cookie if it was modified
        if session is not None and session.modified:
            self._session_manager.save_session(session, response)

        await response(scope, receive, send)

    def route(self, path: str, methods: List[str] = None) -> Callable:
        def decorator(f: Callable) -> Callable:
            mds: list[str] = methods or ["GET"]

            for method in mds:
                if method not in AVAILABLE_METHODS:
                    raise InvalidMethod(f"Method: '{method}' not recognized.")

                for existing_route in self.routes:
                    if existing_route.path_template == path and existing_route.method == method.upper():
                        raise DuplicateEndpoint(f"Route '{path}' with method '{method}' already exists.")

                self.routes.append(Route(path, method, f))
            return f

        return decorator

    def add_url_rule(
        self, rule: str, endpoint: str = None, view_func: Callable = None, **options
    ):
        """Adds URL rule for compatibility with Flask-SocketIO"""
        methods = options.get("methods", ["GET"])
        if view_func:
            for method in methods:
                if method not in AVAILABLE_METHODS:
                    raise InvalidMethod(f"Method: '{method}' not recognized.")
                for existing_route in self.routes:
                    if existing_route.path_template == rule and existing_route.method == method.upper():
                        raise DuplicateEndpoint(f"Route '{rule}' with method '{method}' already exists.")
                self.routes.append(Route(rule, method, view_func))

    def before_request(self, func: Callable[[Request], Any]) -> Callable[[Request], Any]:
        self.exec_before_request = func
        return func

    def after_request(self, func: Callable[[Request], Any]) -> Callable[[Request], Any]:
        self.exec_after_request = func
        return func

    async def internal_error_handler(self, scope: dict, receive: Callable, send: Callable):
        response = HTMLResponse(self.INTERNAL_ERROR, status_code=500)
        await response(scope, receive, send)

    async def method_not_allowed_handler(self, scope: dict, receive: Callable, send: Callable):
        response = HTMLResponse(self.METHOD_NOT_ALLOWED, status_code=405)
        await response(scope, receive, send)

    async def content_not_found_handler(self, scope: dict, receive: Callable, send: Callable):
        response = HTMLResponse(self.NOT_FOUND, status_code=404)
        await response(scope, receive, send)

    def error_handler(self, http_code: int):
        if not (400 <= http_code <= 599):
            raise InvalidHTTPErrorCode(f"HTTP code {http_code} is not a valid error code (must be 400 - 599)")

        def wrapper(func: callable):
            self.error_handlers[http_code] = func 
            return func 

        return wrapper

    async def render_template(self, filename: str, **kwargs) -> HTMLResponse:
        """Renders HTML template with Jinja2"""
        return await render_template(self, filename, **kwargs)

    def on_event(self, event: str) -> Callable:
        """Decorator to register a WebSocket event handler."""

        def decorator(f: Callable) -> Callable:
            self.sio.on(event)(f)
            return f

        return decorator

    def on_connect(self) -> Callable:
        """Decorator to register a WebSocket connect handler."""

        def decorator(f: Callable) -> Callable:
            self.sio.on("connect")(f)
            return f

        return decorator

    def on_disconnect(self) -> Callable:
        """Decorator to register a WebSocket disconnect handler."""

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
        if broadcast:
            await self.sio.emit(event, data)
        elif to:
            await self.sio.emit(event, data, to=to)
        else:
            await self.sio.emit(event, data)


def run_dev(app: Nebula, host: str = "127.0.0.1", port: int = 5000):
    uvicorn.run(app, host=host, port=port)
