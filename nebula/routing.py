import re
from typing import Callable, Dict, Any, List, Optional
from .response import PlainTextResponse

# Pre-compiled pattern to find {param_name} placeholders.
# Defined at module level so it is compiled exactly once for the entire process.
_PARAM_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

class Route:
    __slots__ = (
        "path_template",
        "method",
        "handler",
        "return_class",
        "is_async",
        "path_regex",
        "param_names",
        "_is_static",   # True -> no params; match() skips groupdict() allocation
        "accepts_request_arg",    )

    def __init__(self, path: str, method: str, handler: Callable, return_class = PlainTextResponse, is_async: bool = False):
        self.path_template = path
        self.method = method.upper()  
        self.handler = handler
        self.return_class = return_class
        self.is_async = is_async
        self.accepts_request_arg = False # Will be set by Nebula.route()

        self.path_regex, self.param_names = self._compile_path(path)
        self._is_static = len(self.param_names) == 0

    @staticmethod
    def _compile_path(path: str):
        """Compile a path template into a regex and a param-name list.

        Example:

        "/users/{user_id}/posts/{post_id}"
          regex  -> ^/users/(?P<user_id>[^/]+)/posts/(?P<post_id>[^/]+)$
          params -> ["user_id", "post_id"]
        """
        param_names: List[str] = []

        if "{" not in path:
            return re.compile("^" + re.escape(path) + "$"), param_names

        regex_parts: List[str] = []
        last_idx = 0

        for m in _PARAM_RE.finditer(path):
            static = path[last_idx:m.start()]
            if static:
                regex_parts.append(re.escape(static))

            name = m.group(1)
            param_names.append(name)
            regex_parts.append(f"(?P<{name}>[^/]+)")
            last_idx = m.end()

        tail = path[last_idx:]

        if tail:
            regex_parts.append(re.escape(tail))

        return re.compile("^" + "".join(regex_parts) + "$"), param_names

    def match(self, path: str, method: str) -> Optional[Dict[str, Any]]:
        """Return extracted path params dict if path+method match, else None.

        Convention: callers should pass 'method' already upper-cased so
        the '.upper()' cost is paid once per request, not once per route.
        """

        if self.method != method:
            return None

        m = self.path_regex.match(path)
        if m is None:
            return None

        # Static routes carry no params, avoid the groupdict() allocation
        return {} if self._is_static else m.groupdict()