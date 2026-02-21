from typing import Optional, Dict, Any

import json

from .utils.route import Route


class Data:
    def __init__(self, data: Optional[bytes]):
        self.raw: bytes = data or b""

    def get_json(self) -> dict[str, Any]:
        if not self.raw:
            return {}

        return json.loads(self.raw)

    def text(self) -> str:
        return self.raw.decode("utf-8")

    def bytes(self) -> bytes:
        return self.raw


class Request:
    def __init__(self, route: Route, method: str, data: Optional[Data]):
        self.route = route
        self.method = method
        self.data = data


class Response:
    def __init__(self, body: str, http_code: int, headers: Dict[str, str] = {}):
        self.body = body
        self.http_code = http_code
        self.headers = headers
