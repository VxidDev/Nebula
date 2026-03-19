"""
WebSocket chat with session-based authentication.

Run:
    python examples/chat_auth.py

    # Or with a production WSGI server (eventlet worker):
    gunicorn -w 1 -k eventlet "examples.chat_auth:app.wsgi_app"

Test accounts: alice / password  |  bob / secret
"""

import datetime

from nebula import Nebula, current_user, login_user, logout_user, login_required, UserMixin
from nebula.utils import jsonify
from werkzeug.utils import redirect
from werkzeug.wrappers import Response


# ── App setup ─────────────────────────────────────────────────────────────────

app = Nebula(__file__, "0.0.0.0", 5000, debug=True)
app.init_all()
app.setup_sessions(secret_key="change-me-in-production", max_age=3600)


# ── User model ────────────────────────────────────────────────────────────────

class User(UserMixin):
    def __init__(self, username: str):
        self.id = username
        self.username = username


# In-memory store: username -> password
USERS = {
    "alice": "password",
    "bob":   "secret",
}


@app.user_loader
def load_user(user_id: str):
    if user_id in USERS:
        return User(user_id)
    return None


# ── In-memory chat state ──────────────────────────────────────────────────────

# { sid: username }
connected_users: dict[str, str] = {}
# Last 100 messages
history: list[dict] = []


def _now() -> str:
    return datetime.datetime.now().strftime("%H:%M")


# ── HTTP routes ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return redirect("/chat")


@app.route("/login", methods=["GET", "POST"])
def login():
    from nebula.server import current_request

    if current_user.is_authenticated:
        return redirect("/chat")

    if current_request.method == "POST":
        username = current_request.form.get("username", "").strip()
        password = current_request.form.get("password", "")

        if USERS.get(username) == password:
            login_user(User(username))
            return redirect("/chat")

        return app.render_template("login.html", error="Неверное имя пользователя или пароль")

    return app.render_template("login.html", error=None)


@app.route("/logout")
def logout():
    logout_user()
    return redirect("/login")


@app.route("/chat")
@login_required(redirect_to="/login")
def chat():
    return app.render_template("chat_auth.html", username=current_user.username)


# ── Socket.IO events ──────────────────────────────────────────────────────────

@app.on_connect()
def on_connect(sid, environ):
    session = app.get_session_from_environ(environ)
    username = session.get("_user_id")

    if not username or username not in USERS:
        # Reject unauthenticated WebSocket connections
        return False

    connected_users[sid] = username
    print(f"[WS] {username} connected ({sid})")

    # Send message history to the new client
    app.sio.emit("history", history[-50:], to=sid)

    # Notify others
    app.sio.emit("user_joined", {"username": username}, skip_sid=sid)


@app.on_disconnect()
def on_disconnect(sid):
    username = connected_users.pop(sid, None)
    if username:
        print(f"[WS] {username} disconnected ({sid})")
        app.sio.emit("user_left", {"username": username})


@app.on_event("message")
def on_message(sid, data):
    username = connected_users.get(sid)
    if not username:
        return

    text = str(data.get("message", "")).strip()
    if not text or len(text) > 500:
        return

    msg = {"username": username, "message": text, "time": _now()}
    history.append(msg)
    if len(history) > 100:
        history.pop(0)

    app.sio.emit("new_message", msg)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run()
