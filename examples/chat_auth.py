import datetime

from nebula import Nebula
from nebula.request import Request
from nebula.response import RedirectResponse
from nebula.session import SecureCookieSessionManager, UserMixin, AnonymousUser

app = Nebula(host="0.0.0.0" , port=5000 , debug=True)
app.init_all()
app.setup_sessions(secret_key="change-me-in-production", max_age=3600)

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
async def load_user(user_id: str):
    if user_id in USERS:
        return User(user_id)

    return None


# { sid: username }
connected_users: dict[str, str] = {}
# Last 100 messages
history: list[dict] = []

def _now() -> str:
    return datetime.datetime.now().strftime("%H:%M")


@app.get("/", return_class=RedirectResponse)
async def index():
    return "/chat"

@app.route("/login", methods=["GET", "POST"])
async def login(request: Request):
    if request.user.is_authenticated:
        return RedirectResponse("/chat")

    if request.method == "POST":
        form = await request.form()
        username = form.get("username", "")[0].strip()
        password = form.get("password", "")[0]

        if USERS.get(username) == password:
            request.session[SecureCookieSessionManager._USER_ID_KEY] = User(username).get_id()
            return RedirectResponse("/chat")

        return await app.render_template_async("login.html", error="Invalid username or password.")

    return await app.render_template_async("login.html", error=None)

@app.get("/logout", return_class=RedirectResponse)
async def logout(request: Request):
    if SecureCookieSessionManager._USER_ID_KEY in request.session:
        request.session.pop(SecureCookieSessionManager._USER_ID_KEY)

    return "/login"

@app.get("/chat")
async def chat(request: Request):
    if not request.user.is_authenticated:
        return RedirectResponse("/login")

    return await app.render_template_async("chat_auth.html", username=request.user.username)

@app.on_connect()
async def on_connect(sid, environ):
    scope = environ["asgi.scope"]

    request = Request(scope, None, None)

    session = None
    user = AnonymousUser()

    if app._session_manager:
        session = app._session_manager.open_session(request)

        if app._user_loader and SecureCookieSessionManager._USER_ID_KEY in session:
            loaded = await app._user_loader(session[SecureCookieSessionManager._USER_ID_KEY])
            if loaded:
                user = loaded

    if user.is_authenticated:
        connected_users[sid] = user.username
        print(f"[WS] Authenticated {user.username} ({sid})")
    else:
        print(f"[WS] Anonymous connection ({sid})")

    await app.sio.emit("history", history[-50:], to=sid)

@app.on_disconnect()
async def on_disconnect(sid):
    username = connected_users.pop(sid, None)
    if username:
        print(f"[WS] {username} disconnected ({sid})")
        await app.sio.emit("user_left", {"username": username})

@app.on_event("message")
async def on_message(sid, data):
    print("[WS] Sending message...")
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

    await app.sio.emit("new_message", msg)

if __name__ == "__main__":
    app.run()
