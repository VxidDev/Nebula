import orjson
from typing import AsyncGenerator, Callable, Dict, Any, List
from .exceptions import RequestDisconnected

def _parse_pairs(raw: str) -> "MultiDict":
    """Parse a key=value&... string into a MultiDict.

    Shared by query_params and form so the logic lives in one place.
    """
    md = MultiDict()
    for part in raw.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            md.add(k, v)
        elif part:
            md.add(part, "")
    return md

class MultiDict(dict):
    """dict subclass that supports multiple values per key."""

    __slots__ = ()   # no extra instance dict, saves memory for many instances

    def add(self, key: str, value: Any) -> None:
        if key in self:
            self[key].append(value)
        else:
            self[key] = [value]

    def getlist(self, key: str) -> List[Any]:
        return self.get(key, [])

    # __repr__ from dict is fine; the custom one added no value

class Request:
    """Wraps an ASGI scope/receive/send triple.

    All expensive properties are computed lazily and cached via sentinel
    attributes set in __init__ (faster than hasattr / @functools.cached_property
    because attribute lookup on a known slot/dict key is a single LOAD_ATTR).
    """

    __slots__ = (
        "scope",
        "_receive",
        "_send",
        # Eagerly cached cheap attrs
        "method",
        "path",
        # Lazily populated, None means "not yet computed"
        "_body",
        "_json",
        "_form",
        "_url",
        "_query_string",
        "_query_params",
        "_headers",
        "_cookies",

        # Set externally by Nebula after session/auth resolution
        "session",
        "user",
        "state", # New: A dictionary to hold arbitrary request-specific data
    )

    def __init__(self, scope: dict, receive: Callable, send: Callable):
        self.scope = scope
        self._receive = receive
        self._send = send

        # Cache the two most-accessed fields immediately, they are read on
        # every single request by the router and middleware.
        if self.scope["type"] == "http":
            self.method = scope["method"] 
        elif self.scope["type"] == "websocket":
            self.method = "websocket"
        else:
            self.method = None

        self.path = scope["path"]

        self._body = None
        self._json = None
        self._form = None
        self._url = None
        self._query_string = None
        self._query_params = None
        self._headers = None
        self._cookies = None

        self.session = None
        self.user = None
        self.state: Dict[str, Any] = {} # Initialize state as an empty dictionary

    @property
    def url(self) -> str:
        if self._url is not None:
            return self._url

        scope = self.scope
        scheme = scope.get("scheme", "http")
        server = scope.get("server") or ("", None)
        host, port = server[0], server[1]
        path = scope.get("root_path", "") + self.path
        qs = self.query_string

        parts = [scheme, "://", host]
        if port and port not in (80, 443):
            parts += [":", str(port)]
        parts.append(path)
        if qs:
            parts += ["?", qs]

        self._url = "".join(parts)
        return self._url

    @property
    def query_string(self) -> str:
        if self._query_string is None:
            # decode once; latin-1 is the correct ASGI encoding for raw bytes
            self._query_string = self.scope["query_string"].decode("latin-1")
        return self._query_string

    @property
    def query_params(self) -> MultiDict:
        if self._query_params is None:
            qs = self.query_string
            self._query_params = _parse_pairs(qs) if qs else MultiDict()
        return self._query_params

    @property
    def headers(self) -> Dict[str, str]:
        if self._headers is None:
            # ASGI delivers headers as a list of (bytes, bytes) tuples.
            # Decode all at once; lower() is the HTTP/2 canonical form.
            self._headers = {
                name.decode("latin-1").lower(): value.decode("latin-1")
                for name, value in self.scope["headers"]
            }
        return self._headers

    async def stream(self) -> AsyncGenerator[bytes, None]:
        """Yield raw body chunks as they arrive."""
        while True:
            message = await self._receive()
            msg_type = message["type"]
            if msg_type == "http.request":
                body = message.get("body", b"")
                if body:
                    yield body
                if not message.get("more_body", False):
                    break
            elif msg_type == "http.disconnect":
                break
            else:
                raise RequestDisconnected(
                    "Client disconnected during request processing"
                )

    async def body(self) -> bytes:
        if self._body is None:
            chunks: List[bytes] = []
            async for chunk in self.stream():
                chunks.append(chunk)
            # b"".join is faster than repeated concatenation for N chunks
            self._body = b"".join(chunks)
        return self._body

    async def text(self) -> str:
        return (await self.body()).decode("utf-8")

    async def json(self) -> Any:
        if self._json is None:
            self._json = orjson.loads(await self.body())
        return self._json

    async def form(self) -> MultiDict:
        if self._form is None:
            raw = await self.text()
            self._form = _parse_pairs(raw) if raw else MultiDict()
        return self._form

    @property
    def cookies(self) -> Dict[str, str]:
        if self._cookies is None:
            cookies: Dict[str, str] = {}
            header = self.headers.get("cookie")
            if header:
                for crumb in header.split(";"):
                    crumb = crumb.strip()
                    if "=" in crumb:
                        k, v = crumb.split("=", 1)
                        cookies[k] = v
            self._cookies = cookies
        return self._cookies