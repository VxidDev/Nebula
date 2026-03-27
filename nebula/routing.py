import re
from typing import Callable, Dict, Any, List, Optional
from re import Pattern

class Route:
    def __init__(self, path: str, method: str, handler: Callable):
        self.path_template = path
        self.method = method.upper()
        self.handler = handler
        self.path_regex, self.param_names = self._compile_path(path)

    def _compile_path(self, path: str) -> (re.Pattern, List[str]):
        """
        Compiles the path template into a regex and extracts parameter names.
        Example: "/users/{user_id}/posts/{post_id}"
        Regex: "^/users/(?P<user_id>[^/]+)/posts/(?P<post_id>[^/]+)$"
        Param Names: ["user_id", "post_id"]
        """
        param_names = []
        # Replace {param_name} with (?P<param_name>[^/]+)
        # and escape other regex special characters in the path
        regex_parts = []
        last_idx = 0
        for match in re.finditer(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", path):
            # Add static part before the parameter
            regex_parts.append(re.escape(path[last_idx:match.start()]))
            # Add parameter regex group
            param_name = match.group(1)
            param_names.append(param_name)
            regex_parts.append(f"(?P<{param_name}>[^/]+)")
            last_idx = match.end()

        # Add any remaining static part
        if last_idx < len(path):
            regex_parts.append(re.escape(path[last_idx:]))

        regex_pattern = "^" + "".join(regex_parts) + "$"
        return re.compile(regex_pattern), param_names

    def match(self, path: str, method: str) -> Optional[Dict[str, Any]]:
        if self.method != method.upper():
            return None

        match = self.path_regex.match(path)
        if match:
            return match.groupdict()
        return None