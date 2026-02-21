from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .utils.route import Route
from typing import Dict

class Request:
    def __init__(self, route: Route, method: str):
        self.route = route 
        self.method = method

class Response:
    def __init__(self, body: str , http_code: int):
        self.body = body 
        self.http_code = http_code 

class TemplateNotFound(BaseException):
    pass

class Nebula:
    def __init__(self, host: str , port: int, debug: bool = False):
        self.debug = debug

        self.host = host 
        self.port = port 

        self.routes: Dict[str] = {}
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

        self.exec_before_request = None
        self.exec_after_request = None
        self.exec_on_internal_error = self.internal_error_handler

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

                self.server_instance.request = Request(route, self.command)

                if self.server_instance.exec_before_request:
                    try:
                        self.server_instance.exec_before_request(self.server_instance.request)
                    except Exception as e:
                        self.internal_error(e)

                        return
                        

                result: Response = requestedRoute()

                self.send_response(result.http_code)
                self.end_headers()
                self.wfile.write(result.body.encode())

                if self.server_instance.exec_after_request:
                    try:
                        self.server_instance.exec_after_request(self.server_instance.request)
                    except Exception as e:
                        self.internal_error(e)
                        return

                return

            def handle_response(self, response: Response) -> None:
                self.send_response(response.http_code)
                self.end_headers()
                self.wfile.write(response.body.encode())

                return

            def internal_error(self, exception: Exception):
                if self.server_instance.debug:
                    print(str(exception))
                result = self.server_instance.exec_on_internal_error()
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

    def route(self, path: str): # only GET for now. 
        def decorator(func):
            self.routes[path] = func
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

    def before_request(self, func): # func(arg: Request)
        self.exec_before_request = func 
        def wrapper():
            return func

        return wrapper

    def after_request(self, func): # func(arg: Request)
        self.exec_after_request = func 
        def wrapper():
            return func 

        return wrapper

    def internal_error_handler(self, func = None) -> str:
        if func:
            self.exec_on_internal_error = func
        
        return Response(self.INTERNAL_ERROR , 500)