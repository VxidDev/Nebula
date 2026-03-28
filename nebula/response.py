import orjson
from typing import Dict, Optional

class Response:
    """ASGI HTTP response.

    Headers are encoded to bytes exactly once at construction time and stored
    as the ready-to-send list, so __call__ does zero encoding work per request.
    """

    __slots__ = ("status_code", "body", "_encoded_headers")

    def __init__(
        self,
        content: bytes | str = b"",
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
    ):
        self.status_code = status_code

        # Normalise body to bytes once
        if isinstance(content, str):
            body = content.encode("utf-8")
            effective_media_type = media_type or "text/plain"
        else:
            body = content
            effective_media_type = media_type or "application/octet-stream"
        self.body = body

        # Build the final header list in latin-1 bytes right now.
        # __call__ will send this list as-is, zero encoding on the hot path.
        raw: list[tuple[bytes, bytes]] = []

        if headers:
            for k, v in headers.items():
                raw.append((k.lower().encode("latin-1"), v.encode("latin-1")))

        raw.append((b"content-type",   effective_media_type.encode("latin-1")))
        raw.append((b"content-length", str(len(body)).encode("latin-1")))

        self._encoded_headers = raw

    # Convenience accessor used by session manager and RedirectResponse
    # to append a header after construction (e.g. Set-Cookie, Location).
    def add_header(self, name: str, value: str) -> None:
        self._encoded_headers.append(
            (name.lower().encode("latin-1"), value.encode("latin-1"))
        )

    async def __call__(self, scope, receive, send) -> None:
        await send({
            "type": "http.response.start",
            "status": self.status_code,
            "headers": self._encoded_headers,
        })
        await send({
            "type": "http.response.body",
            "body": self.body,
            "more_body": False,
        })

class HTMLResponse(Response):
    __slots__ = ()

    def __init__(self, content: str | bytes, status_code: int = 200, headers=None):
        super().__init__(content, status_code, headers, "text/html")

class JSONResponse(Response):
    __slots__ = ()

    def __init__(self, content, status_code: int = 200, headers=None):
        super().__init__(orjson.dumps(content), status_code, headers, "application/json")

class PlainTextResponse(Response):
    __slots__ = ()

    def __init__(self, content: str | bytes, status_code: int = 200, headers=None):
        super().__init__(content, status_code, headers, "text/plain")

class RedirectResponse(Response):
    __slots__ = ()

    def __init__(self, url: str, status_code: int = 302, headers=None):
        h = dict(headers) if headers else {}
        h["location"] = url
        super().__init__(b"", status_code, h)