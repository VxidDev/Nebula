from typing import Dict, Any, Union, List, Callable, Optional
import json

class Response:
    def __init__(
        self,
        content: Union[str, bytes] = b"",
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
    ):
        self.status_code = status_code
        self.headers = headers or {}
        self.media_type = media_type

        if isinstance(content, str):
            self.body = content.encode("utf-8")
            if self.media_type is None:
                self.media_type = "text/plain"
        else:
            self.body = content
            if self.media_type is None:
                self.media_type = "application/octet-stream"

        if "content-length" not in self.headers:
            self.headers["content-length"] = str(len(self.body))
        if "content-type" not in self.headers and self.media_type:
            self.headers["content-type"] = self.media_type

    async def __call__(self, scope: dict, receive: Callable, send: Callable):
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": [[k.encode("latin-1"), v.encode("latin-1")] for k, v in self.headers.items()],
            }
        )
        await send({"type": "http.response.body", "body": self.body})


class HTMLResponse(Response):
    def __init__(
        self,
        content: str,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(content, status_code, headers, media_type="text/html")


class JSONResponse(Response):
    def __init__(
        self,
        content: Any,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ):
        json_content = json.dumps(content, ensure_ascii=False).encode("utf-8")
        super().__init__(json_content, status_code, headers, media_type="application/json")


class PlainTextResponse(Response):
    def __init__(
        self,
        content: str,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(content, status_code, headers, media_type="text/plain")


class RedirectResponse(Response):
    def __init__(
        self,
        url: str,
        status_code: int = 302,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(content=b"", status_code=status_code, headers=headers)
        self.headers["location"] = url