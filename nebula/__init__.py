from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .utils.route import Route
from typing import Dict

class HttpServer:
    def __init__(self, host: str , port: int):
        self.host = host 
        self.port = port 

        self.routes: Dict[str] = {}

        self.NOT_FOUND = """
            <head><title>404 Not Found</title></head>

            <body>
                <h1>Not Found</h1>
                <p>The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.</p>
            </body>
        """

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

                result = requestedRoute()

                self.send_response(result[1])
                self.end_headers()
                self.wfile.write(result[0].encode())

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

    def route(self, path: str) -> None: # only GET for now. 
        def decorator(func):
            self.routes[path] = func
            return func
        return decorator