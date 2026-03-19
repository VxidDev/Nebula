import eventlet
from eventlet import wsgi as eventlet_wsgi

from typing import Dict, List, Callable, Optional, Any
from pathlib import Path
import mimetypes
import datetime
import ssl

from werkzeug.local import Local, LocalProxy
from werkzeug.wrappers import Request as WerkzeugRequest, Response as WerkzeugResponse
from werkzeug.serving import run_simple
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import NotFound, MethodNotAllowed
import socketio

from .utils.render_template import render_template
from .utils import init_static_serving, init_template_path, init_template_renderer

from .types import (
    AVAILABLE_METHODS,
    DEFAULT_TEMPLATES_DIR,
    DEFAULT_STATICS_DIR,
    DEFAULT_404_BODY,
    DEFAULT_500_BODY,
    DEFAULT_405_BODY,
)
from .exceptions import InvalidMethod, TemplateNotFound
from .session import (
    SecureCookieSessionManager,
    AnonymousUser,
    _session_ctx as _sess_ctx,
)


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

        # Socket.IO — eventlet mode for proper WebSocket support
        self.sio = socketio.Server(cors_allowed_origins="*", async_mode="eventlet")

        self._socketio_handlers = {}

        self.request_log_format = "[ {HTTP_CODE} - {TIME} ] {ENDPOINT} ({METHOD})"

        self._listener = None

        # Session management (disabled until setup_sessions() is called)
        self._session_manager: Optional[SecureCookieSessionManager] = None
        self._user_loader: Optional[Callable] = None

    # ------------------------------------------------------------------
    # Session / Auth API
    # ------------------------------------------------------------------

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
            cookie_name: Cookie name (default: ``nebula_session``).
            max_age: Cookie lifetime in seconds (default: 86400 = 1 day).
            secure: Set the ``Secure`` flag — use ``True`` with HTTPS only.

        Usage::

            app.setup_sessions(secret_key="change-me-in-production")

            @app.user_loader
            def load_user(user_id):
                return User.get(user_id)
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
        return the user object, or ``None`` if the user no longer exists.

        Usage::

            @app.user_loader
            def load_user(user_id):
                return users.get(user_id)
        """
        self._user_loader = func
        return func

    def get_session_from_environ(self, environ: dict) -> "Session":
        """Parse and return a session from a raw WSGI environ dict.

        Useful inside Socket.IO handlers where Nebula's request context is
        not active but the original HTTP handshake environ is available::

            @app.on_connect()
            def on_connect(sid, environ):
                session = app.get_session_from_environ(environ)
                username = session.get("username")
        """
        if self._session_manager is None:
            raise RuntimeError(
                "Sessions are not configured. Call app.setup_sessions() first."
            )
        return self._session_manager.open_session_from_environ(environ)

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def init_all(
        self,
        static_endpoint: str = "static",
        static_dir: Optional[str] = None,
        template_dir: Optional[str] = None,
    ):
        static_serve_dir = self.statics_dir if not static_dir else static_dir
        init_static_serving(self, current_request, static_endpoint, static_serve_dir)

        template_loc = self.templates_dir if not template_dir else template_dir
        init_template_path(self, template_loc)

        init_template_renderer(self)

        return

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    @property
    def wsgi_app(self):
        """WSGI callable for production deployment.

        Use with an **eventlet** or **gevent** worker so that WebSocket
        connections are handled correctly.

        Gunicorn example (eventlet worker)::

            gunicorn -w 1 -k eventlet "myapp:app.wsgi_app"

        uWSGI example::

            uwsgi --http :5000 --gevent 100 --module myapp:app.wsgi_app

        When deploying this way, add ``eventlet.monkey_patch()`` at the very
        top of your entry-point *before* any other imports.
        """
        return socketio.WSGIApp(self.sio, self)

    def run(self, host=None, port=None, debug=None, ssl_context=None, **kwargs):
        # eventlet monkey-patching must happen before any network I/O
        eventlet.monkey_patch()

        if host is None:
            host = self.host
        if port is None:
            port = self.port
        if debug is None:
            debug = self.debug

        wsgi_app = socketio.WSGIApp(self.sio, self)

        self._listener = eventlet.listen((host, port))

        if ssl_context:
            if isinstance(ssl_context, tuple):
                certfile, keyfile = ssl_context
                self._listener = eventlet.wrap_ssl(
                    self._listener,
                    certfile=certfile,
                    keyfile=keyfile,
                    server_side=True,
                )
            elif isinstance(ssl_context, ssl.SSLContext):
                self._listener = eventlet.wrap_ssl(
                    self._listener,
                    server_side=True,
                    ssl_context=ssl_context,
                )
            else:
                raise ValueError("ssl_context must be a tuple or ssl.SSLContext")

            print(f"Starting Nebula server on https://{host}:{port}")
        else:
            print(f"Starting Nebula server on http://{host}:{port}")

        try:
            eventlet_wsgi.server(self._listener, wsgi_app, log_output=debug)
        except OSError:
            pass

    def stop(self):
        """Stop the eventlet server.

        Must be called from a different thread than the one running the server.
        """
        if self._listener:
            self._listener.close()

    # ------------------------------------------------------------------
    # Request dispatch
    # ------------------------------------------------------------------

    def dispatch_request(self, request: WerkzeugRequest):
        _request_ctx_stack.request = request

        # Open session and resolve current user
        session = None
        if self._session_manager:
            session = self._session_manager.open_session(request)
            _sess_ctx.session = session

            user = AnonymousUser()
            if self._user_loader and SecureCookieSessionManager._USER_ID_KEY in session:
                loaded = self._user_loader(
                    session[SecureCookieSessionManager._USER_ID_KEY]
                )
                if loaded is not None:
                    user = loaded
            _sess_ctx.user = user

        with request:
            adapter = self.url_map.bind_to_environ(request.environ)
            try:
                endpoint, values = adapter.match()

                if self.exec_before_request:
                    self.exec_before_request()

                response = self.view_functions[endpoint](**values)

                # Log request
                try:
                    query = request.query_string.decode("utf-8")
                    path = f"{request.path}?{query}" if query else request.path
                    date = datetime.datetime.now()
                    print(
                        self.request_log_format.format(
                            ENDPOINT=path,
                            HTTP_CODE=response.status_code,
                            TIME=date.strftime("%H:%M:%S"),
                            DATE=date.strftime("%Y-%m-%d"),
                            METHOD=request.method,
                        )
                    )
                except Exception as e:
                    print(f"Invalid log format string! - {str(e)}")

                if self.exec_after_request:
                    self.exec_after_request()

                if not isinstance(response, WerkzeugResponse):
                    response = WerkzeugResponse(str(response), 200)

            except NotFound:
                response = self.error_handlers[404]()
            except MethodNotAllowed:
                response = self.error_handlers[405]()
            except Exception as e:
                print(e)
                response = self.error_handlers[500]()

            # Persist session to cookie if it was modified
            if session is not None and session.modified:
                self._session_manager.save_session(session, response)

            return response

    def __call__(self, environ, start_response):
        request = WerkzeugRequest(environ)

        with request:
            response = self.dispatch_request(request)
            return response(environ, start_response)

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

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

    def add_url_rule(
        self, rule: str, endpoint: str = None, view_func: Callable = None, **options
    ):
        """Adds URL rule for compatibility with Flask-SocketIO"""
        if endpoint is None:
            endpoint = view_func.__name__
        methods = options.get("methods", ["GET"])
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

    # ------------------------------------------------------------------
    # Error handlers
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Templates
    # ------------------------------------------------------------------

    def render_template(self, filename: str, **kwargs) -> WerkzeugResponse:
        """Renders HTML template with Jinja2"""
        return render_template(self, filename, **kwargs)

    # ------------------------------------------------------------------
    # Socket.IO
    # ------------------------------------------------------------------

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

    def emit(
        self,
        event: str,
        data: Any = None,
        to: str = None,
        broadcast: bool = False,
    ):
        """Send a Socket.IO event."""
        if broadcast:
            self.sio.emit(event, data)
        elif to:
            self.sio.emit(event, data, to=to)
        else:
            self.sio.emit(event, data)
