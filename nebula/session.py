import json
import hmac
import hashlib
import base64
from functools import wraps
from typing import Any, Optional, Callable

from werkzeug.local import Local, LocalProxy
from werkzeug.wrappers import Response as WerkzeugResponse


_session_ctx = Local()
current_session: "Session" = LocalProxy(lambda: _session_ctx.session)
current_user: "UserMixin | AnonymousUser" = LocalProxy(lambda: _session_ctx.user)


class Session(dict):
    """Cookie-based session dictionary that tracks modifications."""

    modified: bool = False

    def __setitem__(self, key: str, value: Any) -> None:
        self.modified = True
        super().__setitem__(key, value)

    def __delitem__(self, key: str) -> None:
        self.modified = True
        super().__delitem__(key)

    def clear(self) -> None:
        self.modified = True
        super().clear()

    def pop(self, key: str, *args) -> Any:
        self.modified = True
        return super().pop(key, *args)

    def update(self, *args, **kwargs) -> None:
        self.modified = True
        super().update(*args, **kwargs)


class UserMixin:
    """Mixin for user model classes to work with the session system.

    Usage::

        class User(UserMixin):
            def __init__(self, id, name):
                self.id = id
                self.name = name

        @app.user_loader
        def load_user(user_id):
            return User.get(user_id)
    """

    is_authenticated: bool = True
    is_active: bool = True
    is_anonymous: bool = False

    def get_id(self) -> str:
        try:
            return str(self.id)
        except AttributeError:
            raise NotImplementedError(
                "UserMixin requires an 'id' attribute or override of get_id()"
            )


class AnonymousUser:
    """Represents an unauthenticated (anonymous) user."""

    is_authenticated: bool = False
    is_active: bool = False
    is_anonymous: bool = True

    def get_id(self) -> None:
        return None


class SecureCookieSessionManager:
    """Manages HMAC-signed cookie-based sessions."""

    _USER_ID_KEY = "_user_id"

    def __init__(
        self,
        secret_key: str,
        cookie_name: str = "nebula_session",
        max_age: int = 86400,
        secure: bool = False,
    ):
        self.secret_key = (
            secret_key.encode() if isinstance(secret_key, str) else secret_key
        )
        self.cookie_name = cookie_name
        self.max_age = max_age
        self.secure = secure

    def _sign(self, data: str) -> str:
        sig = hmac.new(self.secret_key, data.encode(), hashlib.sha256).hexdigest()
        return f"{data}.{sig}"

    def _verify(self, signed: str) -> Optional[str]:
        try:
            data, sig = signed.rsplit(".", 1)
            expected = hmac.new(
                self.secret_key, data.encode(), hashlib.sha256
            ).hexdigest()
            if hmac.compare_digest(sig, expected):
                return data
        except Exception:
            pass
        return None

    def _decode_cookie(self, cookie_value: str) -> Optional[Session]:
        verified = self._verify(cookie_value)
        if verified:
            try:
                padded = verified + "=" * (-len(verified) % 4)
                raw = base64.urlsafe_b64decode(padded.encode()).decode()
                return Session(json.loads(raw))
            except Exception:
                pass
        return None

    def open_session(self, request) -> Session:
        cookie = request.cookies.get(self.cookie_name)
        if cookie:
            session = self._decode_cookie(cookie)
            if session is not None:
                return session
        return Session()

    def open_session_from_environ(self, environ: dict) -> Session:
        """Parse session from a raw WSGI environ (e.g. inside Socket.IO handlers)."""
        from http.cookies import SimpleCookie

        raw_cookie = environ.get("HTTP_COOKIE", "")
        if raw_cookie:
            jar = SimpleCookie()
            jar.load(raw_cookie)
            morsel = jar.get(self.cookie_name)
            if morsel:
                session = self._decode_cookie(morsel.value)
                if session is not None:
                    return session
        return Session()

    def save_session(self, session: Session, response: WerkzeugResponse) -> None:
        payload = (
            base64.urlsafe_b64encode(json.dumps(dict(session)).encode())
            .decode()
            .rstrip("=")
        )
        signed = self._sign(payload)
        response.set_cookie(
            self.cookie_name,
            signed,
            max_age=self.max_age,
            httponly=True,
            samesite="Lax",
            secure=self.secure,
        )


def login_user(user) -> None:
    """Store the user's ID in the current session.

    Usage::

        @app.route("/login", methods=["POST"])
        def login():
            user = User.get_by_credentials(...)
            if user:
                login_user(user)
                return redirect("/dashboard")
    """
    current_session[SecureCookieSessionManager._USER_ID_KEY] = user.get_id()


def logout_user() -> None:
    """Remove the current user from the session.

    Usage::

        @app.route("/logout")
        def logout():
            logout_user()
            return redirect("/login")
    """
    current_session.pop(SecureCookieSessionManager._USER_ID_KEY, None)


def login_required(redirect_to: str = "/login") -> Callable:
    """Decorator that redirects unauthenticated users to the login page.

    Usage::

        @app.route("/dashboard")
        @login_required(redirect_to="/login")
        def dashboard():
            return f"Hello, {current_user.name}!"
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                from werkzeug.utils import redirect as werkzeug_redirect
                return werkzeug_redirect(redirect_to)
            return f(*args, **kwargs)

        return wrapped

    return decorator
