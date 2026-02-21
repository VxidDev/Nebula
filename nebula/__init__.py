from .server import Nebula
from .core import Data, Request, Response
from .exceptions import TemplateNotFound, InvalidMethod
from .types import AVAILABLE_METHODS

import json
import mimetypes


def jsonify(dictionary: dict, status: int = 200) -> Response:
    return Response(
        body=json.dumps(dictionary),
        http_code=status,
        headers={"Content-Type": "application/json"},
    )


__all__ = [
    "Nebula",
    "Data",
    "Request",
    "Response",
    "TemplateNotFound",
    "InvalidMethod",
    "AVAILABLE_METHODS",
    "jsonify",
]
