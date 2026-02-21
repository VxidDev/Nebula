from http.server import BaseHTTPRequestHandler
from typing import TYPE_CHECKING

from .core import Data, Request, Response
from .utils.route import Route

if TYPE_CHECKING:
    from .server import Nebula


class RequestHandler(BaseHTTPRequestHandler):
    server_instance: "Nebula" = None

    def do_GET(self):
        route = Route(self.path)
        statics_route = str(self.server_instance.statics_dir).rsplit('/', 1)[1]
        is_requesting_statics = route.path.split('/' , 2)[1] == statics_route 

        if is_requesting_statics:
            try:
                result = self.server_instance._statics_handler(route)
                self.handle_response(result)
                return
            except Exception as e:
                self.internal_error(e)
                return

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

        for key, value in response.headers.items():
            self.send_header(key, value)

        self.end_headers()

        if isinstance(response.body, str): 
            self.wfile.write(response.body.encode())
        else:
            self.wfile.write(response.body)

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
