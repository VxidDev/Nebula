from http.server import ThreadingHTTPServer
from typing import Dict, List, Callable, Optional, Any
from pathlib import Path
import mimetypes
import threading

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
        self.exec_on_content_not_found: Callable = self.content_not_found_handler

        self.error_handlers: dict[int, Callable] = {
            404: self.exec_on_content_not_found,
            405: self.exec_on_method_not_allowed,
            500: self.exec_on_internal_error
        }

        self.request: Optional[Request] = None

        RequestHandler.server_instance = self

        self.handler = RequestHandler
        self.thread = None

    def run(self):
        self.server = ThreadingHTTPServer((self.host, self.port), self.handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=False)
        self.thread.start()
        print(f"Server running at http://{self.host}:{self.port}")
        
        try:
            self.thread.join()  # wait here until server is stopped
        except KeyboardInterrupt:
            print("KeyboardInterrupt detected, shutting down server...")
            self.stop()

    def stop(self) -> None:
        if self.thread is None:
            print("Server was never started, nothing to stop.")
            return

        print("Shutting down server...")

        if self.server:
            try:
                self.server.shutdown()      
            except Exception as e:
                print(f"Ignoring shutdown error: {e}")
            try:
                self.server.server_close()  
            except Exception as e:
                print(f"Ignoring server_close error: {e}")

        if self.thread:
            self.thread.join()             # wait for thread to finish

        print("Server stopped safely.")
            
    def route(self, path: str, methods: List[str] = ["GET"]) -> Callable:
        def decorator(func):
            for method in methods:
                if method not in AVAILABLE_METHODS:
                    raise InvalidMethod(f"Method: '{method}' not recognized.")

            self.routes[path] = {"function": func , "methods": methods}
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

    def internal_error_handler(self, func = None) -> Response:
        if func:
            self.exec_on_internal_error = func
            self.error_handlers[500] = func
        
        return Response(self.INTERNAL_ERROR , 500)

    def method_not_allowed_handler(self, func = None) -> Response:
        if func:
            self.exec_on_method_not_allowed = func 
            self.error_handlers[405] = func

        return Response(self.METHOD_NOT_ALLOWED , 405)

    def _statics_handler(self, route: Route) -> Optional[Response]:
        if self.debug:
            print(f"Request path: {self.request.route.path}")
            
        parts = route.path.lstrip("/").split("/", 1)

        if len(parts) < 2:
            # No filename specified
            return Response(self.NOT_FOUND, 404)

        rel_path = parts[1]  # e.g., "file.js"
        full_path = Path(self.statics_dir) / rel_path

        if self.debug:
            print(f"Trying to serve static file: {full_path.resolve()}")

        if not full_path.exists() or not full_path.is_file():
            return Response(self.NOT_FOUND, 404)

        mime, _ = mimetypes.guess_type(full_path)

        if not mime:
            # fallback
            ext = full_path.suffix.lower()

            if ext == ".js":
                mime = "application/javascript"

            elif ext == ".css":
                mime = "text/css"

            elif ext in [".html", ".htm"]:
                mime = "text/html"

            else:
                mime = "application/octet-stream"

        if mime.startswith("text/") or mime == "application/javascript":
            mime += "; charset=utf-8"
        
        with open(full_path , "rb") as file:
            content = file.read()

        headers: dict = {
            "Content-Type": mime,
            "Cache-Control": "public, max-age=3600"
        }

        if mime.startswith("text/") or mime == "application/javascript":
            body = content.decode(errors="ignore")
        else:
            body = content

        return Response(
            body=body,
            http_code=200, 
            headers=headers
        )

    def error_handler(self, http_code: int) -> Callable:
        if not (400 <= http_code <= 599):
            raise ValueError("Error handler must be 400-599 status code.")

        def decorator(func: Callable) -> Callable:
            self.error_handlers[http_code] = func
            return func 
        
        return decorator

    def content_not_found_handler(self, func = None) -> Callable:
        if func:
            self.exec_on_content_not_found = func
            self.error_handlers[404] = func
        
        return Response(self.NOT_FOUND , 404)
