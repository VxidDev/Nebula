import json
import json
from typing import AsyncGenerator, Tuple, List, Dict, Any, Optional, Callable

class MultiDict(dict):
    """
    A simple MultiDict implementation that allows multiple values for the same key.
    """
    def add(self, key: str, value: Any):
        if key not in self:
            self[key] = []
        self[key].append(value)

    def getlist(self, key: str) -> List[Any]:
        return self.get(key, [])

    def __repr__(self):
        return f"MultiDict({super().__repr__()})"
from typing import AsyncGenerator, Tuple, List, Dict, Any, Optional

class Request:
    def __init__(self, scope: dict, receive: Callable, send: Callable):
        self.scope = scope
        self._receive = receive
        self._send = send
        self._body = None
        self._form = None
        self._json = None

    @property
    def method(self) -> str:
        return self.scope["method"]

    @property
    def url(self) -> str:
        # Reconstruct URL from scope
        scheme = self.scope.get("scheme", "http")
        server = self.scope.get("server", ["", None])
        host = server[0]
        port = server[1]
        path = self.scope.get("root_path", "") + self.scope.get("path", "")
        query_string = self.scope.get("query_string", b"").decode("latin-1")

        url = f"{scheme}://{host}"
        if port and port not in (80, 443):
            url += f":{port}"
        url += path
        if query_string:
            url += f"?{query_string}"
        return url

    @property
    def path(self) -> str:
        return self.scope["path"]

    @property
    def query_string(self) -> str:
        return self.scope["query_string"].decode("latin-1")

    @property
    def query_params(self) -> MultiDict:
        if not hasattr(self, "_query_params"):
            query_string = self.query_string
            self._query_params = MultiDict()
            if query_string:
                for param in query_string.split("&"):
                    if "=" in param:
                        key, value = param.split("=", 1)
                        self._query_params.add(key, value)
                    else:
                        self._query_params.add(param, "")
        return self._query_params

    @property
    def headers(self) -> Dict[str, str]:
        if not hasattr(self, "_headers"):
            self._headers = {}
            for name, value in self.scope["headers"]:
                self._headers[name.decode("latin-1").lower()] = value.decode("latin-1")
        return self._headers

    async def stream(self) -> AsyncGenerator[bytes, None]:
        while True:
            message = await self._receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                if body:
                    yield body
                if not message.get("more_body", False):
                    break
            elif message["type"] == "http.disconnect":
                break
            else:
                # Handle other message types if necessary, or raise an error
                pass # Or raise a RequestDisconnected exception

    async def body(self) -> bytes:
        if self._body is None:
            chunks = []
            async for chunk in self.stream():
                chunks.append(chunk)
            self._body = b"".join(chunks)
        return self._body

    async def text(self) -> str:
        return (await self.body()).decode("utf-8")

    async def json(self) -> Any:
        if self._json is None:
            self._json = json.loads(await self.body())
        return self._json

    async def form(self) -> MultiDict:
        if self._form is None:
            body = await self.text()
            self._form = MultiDict()
            if body:
                for param in body.split("&"):
                    if "=" in param:
                        key, value = param.split("=", 1)
                        self._form.add(key, value)
                    else:
                        self._form.add(param, "")
        return self._form

    @property
    def cookies(self) -> Dict[str, str]:
        if not hasattr(self, "_cookies"):
            self._cookies = {}
            cookie_header = self.headers.get("cookie")
            if cookie_header:
                for cookie in cookie_header.split(";"):
                    if "=" in cookie:
                        key, value = cookie.strip().split("=", 1)
                        self._cookies[key] = value
        return self._cookies
