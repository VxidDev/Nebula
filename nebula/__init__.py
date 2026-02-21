from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .utils.route import Route
from typing import Dict , List, Callable, Optional

import json

AVAILABLE_METHODS = ["GET" , "POST"]

class Data:
    def __init__(self, data: Optional[bytes]):
        self.raw: bytes = data or b""

    def get_json(self) -> dict[str, any]:
        if not self.raw:
            return {}

        return json.loads(self.raw)

    def text(self) -> str:
        return self.raw.decode("utf-8")

    def bytes(self) -> bytes:
        return self.raw

class Request:
    def __init__(self, route: Route, method: str , data: Optional[Data]):
        self.route = route 
        self.method = method

        self.data = data

class Response:
    def __init__(self, body: str , http_code: int, headers: dict = {}):
        self.body = body 
        self.http_code = http_code 
        self.headers = headers

class TemplateNotFound(BaseException):
    pass

class InvalidMethod(BaseException):
    pass

class Nebula:
    def __init__(self, host: str , port: int, debug: bool = False):
        self.debug = debug

        self.host = host 
        self.port = port 

        self.routes: Dict[str, Dict[str, Any]] = {}
        self.templates_dir = "./templates"

        self.NOT_FOUND = """
            <head><title>404 Not Found</title></head>

            <body>
                <h1>Not Found</h1>
                <p>The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.</p>
            </body>
        """

        self.INTERNAL_ERROR = """
            <head><title>500 Internal Server Error</title></head>

            <body>
                <h1>Internal Server Error</h1>
                <p>The server encountered an unexpected condition that prevented it from fulfilling the request.</p>
                <p>Please try again later.</p>
            </body>
        """

        self.METHOD_NOT_ALLOWED = """
            <head><title>405 Method Not Allowed</title></head>

            <body>
                <h1>Method Not Allowed</h1>
                <p>The requested HTTP method is not supported for this URL.</p>
            </body>
        """

        self.exec_before_request = None
        self.exec_after_request = None
        self.exec_on_internal_error = self.internal_error_handler
        self.exec_on_method_not_allowed = self.method_not_allowed_handler

        self.request = None

        class Handler(BaseHTTPRequestHandler):
            server_instance: "HttpServer" = None

            def do_GET(self):
                route = Route(self.path)
                requestedRoute = self.server_instance.routes.get(route.path, None)

                if not requestedRoute:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(f"{self.server_instance.NOT_FOUND}".encode())
                    return

                if "GET" not in requestedRoute["methods"]:
                    self.method_not_allowed()
                    return

                self.server_instance.request = Request(route, self.command, None)

                try:
                    if self.server_instance.exec_before_request:
                        self.server_instance.exec_before_request(self.server_instance.request)
                            
                    result: Response = requestedRoute["function"]()

                    self.send_response(result.http_code)

                    for key, value in result.headers.items():
                        self.send_header(key, value)

                    self.end_headers()
                    self.wfile.write(result.body.encode())

                    if self.server_instance.exec_after_request:
                        self.server_instance.exec_after_request(self.server_instance.request)

                    return
                except Exception as e:
                    self.internal_error(e)
                    return

            def do_POST(self):
                route = Route(self.path)
                requestedRoute = self.server_instance.routes.get(route.path, None)

                if not requestedRoute:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(f"{self.server_instance.NOT_FOUND}".encode())
                    return

                if "POST" not in requestedRoute["methods"]:
                    self.method_not_allowed()
                    return

                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length)

                self.server_instance.request = Request(route, self.command, Data(body))

                try:
                    if self.server_instance.exec_before_request:
                        self.server_instance.exec_before_request(self.server_instance.request)
                            
                    result: Response = requestedRoute["function"]()

                    self.send_response(result.http_code)

                    for key, value in result.headers.items():
                        self.send_header(key, value)

                    self.end_headers()
                    self.wfile.write(result.body.encode())

                    if self.server_instance.exec_after_request:
                        self.server_instance.exec_after_request(self.server_instance.request)

                    return
                except Exception as e:
                    self.internal_error(e)
                    return

            def handle_response(self, response: Response) -> None:
                self.send_response(response.http_code)
                self.end_headers()
                self.wfile.write(response.body.encode())

                return

            def internal_error(self, exception: Exception) -> None:
                if self.server_instance.debug:
                    print(str(exception))
                result: Response = self.server_instance.exec_on_internal_error()
                self.handle_response(result)

                return

            def method_not_allowed(self) -> None:
                result: Response = self.server_instance.exec_on_method_not_allowed()
                self.handle_response(result)
                return

        Handler.server_instance = self
        self.handler = Handler
        self.server = ThreadingHTTPServer((self.host , self.port), self.handler)

    def run(self) -> None:
        try:
            print(f"Server is up! - http://{self.host}:{self.port}")
            self.server.serve_forever()
        except KeyboardInterrupt:
            self.server.shutdown()

    def route(self, path: str, methods: List[str] = ["GET"]) -> Callable: # only GET for now. 
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

    def before_request(self, func) -> Callable: # func(arg: Request)
        self.exec_before_request = func 
        def wrapper():
            return func

        return wrapper

    def after_request(self, func) -> Callable: # func(arg: Request)
        self.exec_after_request = func 
        def wrapper():
            return func 

        return wrapper

    def internal_error_handler(self, func = None) -> Response:
        if func:
            self.exec_on_internal_error = func
        
        return Response(self.INTERNAL_ERROR , 500)

    def method_not_allowed_handler(self, func = None) -> Response:
        if func:
            self.exec_on_method_not_allowed = func 

        return Response(self.METHOD_NOT_ALLOWED , 405)

def jsonify(dictionary: dict , status: int = 200) -> Response:
    return Response(
        body=json.dumps(dictionary),
        http_code=status,
        headers={"Content-Type": "application/json"} 
    )
