from typing import Callable, Dict, Any, List, Optional, Tuple
from .middleware import Middleware

PATH_CONVERTERS = {
    "int": int,
    "float": float,
    "str": str,
    "path": lambda x: x,
}


class Route:
    __slots__ = (
        "path_template",
        "method",
        "handler",
        "return_class",
        "is_async",
        "compiled_pattern",  # [(param_name, converter) or None for static parts]
        "pattern_parts",  # список оригинальных сегментов для статического сравнения
        "_is_static",
        "accepts_request_arg",
        "middlewares",
    )

    def __init__(
        self,
        path: str,
        method: str,
        handler: Callable,
        return_class=None,
        is_async: bool = False,
    ):
        self.path_template = path
        self.method = method.upper()
        self.handler = handler
        self.return_class = return_class
        self.is_async = is_async
        self.accepts_request_arg = False
        self.middlewares: List["Middleware"] = []

        self.compiled_pattern, self.pattern_parts = self._compile_path(path)
        self._is_static = all(item is None for item in self.compiled_pattern)

    @staticmethod
    def _compile_path(path: str) -> Tuple[List, List[str]]:
        """Compile a path template into an optimized structure.

        Returns:
            - compiled: list where each element is (param_name, converter) or None for static parts
            - pattern_parts: list of path segments for static comparison

        Example:
            "/users/{user_id}/posts/{post_id:int}"
            -> compiled: [None, ('user_id', str), None, ('post_id', int)]
            -> parts: ['users', '{user_id}', 'posts', '{post_id:int}']
        """
        parts = path.strip("/").split("/")
        compiled: List = []

        for part in parts:
            if part.startswith("{") and part.endswith("}"):
                # Dynamic parameter
                inner = part[1:-1]
                if ":" in inner:
                    param_name, param_type = inner.split(":", 1)
                    if param_type not in PATH_CONVERTERS:
                        raise ValueError(f"Unknown path type: {param_type}")
                    converter = PATH_CONVERTERS[param_type]
                else:
                    param_name = inner
                    converter = str
                compiled.append((param_name, converter))
            else:
                compiled.append(None)

        return compiled, parts

    def match(self, path: str, method: str) -> Optional[Dict[str, Any]]:
        """Return extracted path params dict if path+method match, else None.

        Convention: callers should pass 'method' already upper-cased so
        the '.upper()' cost is paid once per request, not once per route.
        """
        if self.method != method:
            return None

        path_parts = path.strip("/").split("/")

        if len(path_parts) != len(self.pattern_parts):
            return None

        path_params: Dict[str, Any] = {}

        for compiled_item, pattern_part, path_part in zip(
            self.compiled_pattern, self.pattern_parts, path_parts
        ):
            if compiled_item is not None:
                # Dynamic parameter
                param_name, converter = compiled_item
                try:
                    path_params[param_name] = converter(path_part)
                except (ValueError, TypeError):
                    return None
            elif pattern_part != path_part:
                # Static part mismatch
                return None

        return path_params if path_params else None


class RouteGroup:
    def __init__(
        self,
        app: "Nebula",
        prefix: str,
        middlewares: list["Middleware"] | None = None,
    ) -> None:
        self.app: "Nebula" = app
        self.prefix: str = prefix
        self._middlewares = middlewares or []

    def middleware(self, middleware: "Middleware") -> "Middleware":
        self._middlewares.append(middleware)
        return middleware

    def get(
        self,
        path: str,
        return_class=None,
        route_middlewares: list["Middleware"] | None = None,
    ) -> Callable:
        return self.app.route(
            f"{self.prefix}{path}",
            ["GET"],
            return_class,
            group_middlewares=self._middlewares,
            route_middlewares=route_middlewares,
        )

    def post(
        self,
        path: str,
        return_class=None,
        route_middlewares: list["Middleware"] | None = None,
    ) -> Callable:
        return self.app.route(
            f"{self.prefix}{path}",
            ["POST"],
            return_class,
            group_middlewares=self._middlewares,
            route_middlewares=route_middlewares,
        )

    def put(
        self,
        path: str,
        return_class=None,
        route_middlewares: list["Middleware"] | None = None,
    ) -> Callable:
        return self.app.route(
            f"{self.prefix}{path}",
            ["PUT"],
            return_class,
            group_middlewares=self._middlewares,
            route_middlewares=route_middlewares,
        )

    def delete(
        self,
        path: str,
        return_class=None,
        route_middlewares: list["Middleware"] | None = None,
    ) -> Callable:
        return self.app.route(
            f"{self.prefix}{path}",
            ["DELETE"],
            return_class,
            group_middlewares=self._middlewares,
            route_middlewares=route_middlewares,
        )

    def route(
        self,
        path: str,
        methods: List[str] = None,
        return_class=None,
        route_middlewares: list["Middleware"] | None = None,
    ) -> Callable:
        return self.app.route(
            f"{self.prefix}{path}",
            methods,
            return_class,
            group_middlewares=self._middlewares,
            route_middlewares=route_middlewares,
        )
