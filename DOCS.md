## Documentation

Documentation for Nebula's features.

### Middleware Support

Nebula supports middleware for processing requests and responses. Middleware classes should inherit from `BaseMiddleware` and implement an ASGI-compatible `__call__` method.

```python
import datetime
from nebula import Nebula
from nebula.request import Request
from nebula.middleware import Middleware, BaseMiddleware

# A simple logging middleware
class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            start_time = datetime.datetime.now()
            print(f"[{start_time}] Request started for {scope['path']}")

            await super().__call__(scope, receive, send)

            end_time = datetime.datetime.now()
            duration = end_time - start_time
            print(f"[{end_time}] Request finished for {scope['path']} in {duration.total_seconds():.4f} seconds")
        else:
            await super().__call__(scope, receive, send)

# Another middleware example, specific to API routes
class APILoggerMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            start_time = datetime.datetime.now()
            print(f"[{start_time}] Handling API request... {scope['path']}")

            await super().__call__(scope, receive, send)
        else:
            await super().__call__(scope, receive, send)

app = Nebula(
    middlewares = [
        Middleware(LoggingMiddleware) # Applied globally to all routes
    ]
)

# Apply middleware to a group of routes
api = app.group(
    "/api",
    middlewares = [
        Middleware(APILoggerMiddleware)
    ]
)

@app.get("/")
async def home():
    return "<h1>Hello from Nebula with Logging Middleware!</h1>"

@api.get("/greet/{name}")
async def greet(name: str):
    return {"greeting": f"Hi, {name}!"}

# You can also apply middleware to a single route using the `route_middlewares` argument
@app.get("/users/{user_id}", route_middlewares=[Middleware(APILoggerMiddleware)])
async def get_user(request: Request, user_id: int):
    return f"User ID: {user_id}"

if __name__ == "__main__":
    app.run()
```

### Applying Middleware

Middleware can be applied at different levels:

*   **Global Middleware**: Passed during `Nebula` initialization, affecting all requests.
*   **Group-Specific Middleware**: Applied to a group of routes using `app.group()`.
*   **Route-Specific Middleware**: Applied to an individual route using the `route_middlewares` argument in route decorators (e.g., `@app.get()`, `@app.post()`).

### Session Management

Nebula provides secure session management using HMAC-signed cookies. You need to set a `SECRET_KEY` and call `setup_sessions`. It also offers utilities for user session management via `UserMixin` and `app.user_loader`.

```python
from nebula import Nebula, SecureCookieSessionManager, UserMixin
from nebula.request import Request
from nebula.response import RedirectResponse

app = Nebula()
# IMPORTANT: Use a strong, unique secret key and manage its security.
app.setup_sessions(secret_key="your-super-secret-key-change-me", max_age=3600)

# Example User class integrating with UserMixin for session management
class User(UserMixin):
    def __init__(self, user_id: str):
        self.id = user_id # 'id' attribute is used by UserMixin.get_id()
        self.name = f"User {user_id}"

# In a real application, this would load a user from a database
USERS_DB = {
    "1": {"username": "alice", "password": "password123"},
    "2": {"username": "bob", "password": "secret"},
}

@app.user_loader
async def load_user(user_id: str):
    """
    This function is called by Nebula to load a user object from the session.
    """
    for entry in USERS_DB.values():
        if entry["username"] == user_id:
            return User(user_id)
            
    return None

@app.get("/login")
async def login(request: Request):
    # If the user is already authenticated, redirect them
    if request.user.is_authenticated:
        return RedirectResponse("/profile")
    return "<h1>Login Page</h1><form method='post' action='/do_login'><input type='text' name='user_id'><input type='password' name='password'><button type='submit'>Login</button></form>"

@app.post("/do_login")
async def do_login(request: Request):
    form = await request.form()
    user_id = form.get("user_id", [""])[0]
    password = form.get("password", [""])[0]

    for entry in USERS_DB.values():
        if user_id == entry["username"] and entry["password"] == password:
            # Store the user ID in the session
            request.session[SecureCookieSessionManager._USER_ID_KEY] = User(user_id).get_id()
            return RedirectResponse("/profile")

    return "<p>Invalid credentials.</p> <a href='/login'>Try again</a>"


@app.get("/profile")
async def profile(request: Request):
    # `request.user` is available thanks to `user_loader`
    print(request.user)
    if not request.user.is_authenticated:
        return RedirectResponse("/login")

    return f"<h1>Welcome, {request.user.name}!</h1><p><a href='/logout'>Logout</a></p>"

@app.get("/logout")
async def logout(request: Request):
    # Clear the user ID from the session
    if SecureCookieSessionManager._USER_ID_KEY in request.session:
        request.session.pop(SecureCookieSessionManager._USER_ID_KEY)
    return RedirectResponse("/login")

# --- Example of generic session variable usage ---
@app.get("/session/set")
async def set_session(request: Request):
    request.session["theme"] = "dark"
    return "Session variable 'theme' set to 'dark'."

@app.get("/session/get")
async def get_session(request: Request):
    theme = request.session.get("theme", "light")
    return f"Current theme from session: {theme}"

@app.get("/session/clear_all")
async def clear_all_session(request: Request):
    request.session.clear()
    return "All session variables cleared."

if __name__ == "__main__":
    app.run()
```

### WebSocket Support

Nebula integrates with `python-socketio` for real-time WebSocket communication.

```python
from nebula import Nebula
from nebula.request import Request # Request might not be directly used in handlers but could be in a real app context

app = Nebula()

# Register Socket.IO event handlers
@app.on_connect()
async def connect(sid, environ):
    print(f"Client connected: {sid}")
    await app.emit("message", {"data": "Welcome!"}, to=sid)

@app.on_disconnect()
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

@app.on_event("message")
async def handle_message(sid, message):
    print(f"Message from {sid}: {message}")
    await app.emit("response", {"data": f"Server received: {message['data']}"}, to=sid)

if __name__ == "__main__":
    app.run()
```

### Error Handling

Define custom error handlers for specific HTTP status codes using the `@app.error_handler()` decorator.

```python
from nebula import Nebula
from nebula.request import Request
from nebula.response import HTMLResponse
from nebula.exceptions import HTTPException

app = Nebula()

@app.error_handler(404)
async def custom_not_found_handler(scope, receive, send):
    await HTMLResponse("<h1>Oops! Page not found (404) </h1>", status_code=404)(scope, receive, send)

@app.error_handler(500)
async def custom_server_error_handler(scope, receive, send):
    await HTMLResponse("<h1>Something went wrong (500) </h1>", status_code=500)(scope, receive, send)

@app.get("/")
async def index():
    return "Hello!"

@app.get("/raise_error")
async def raise_error():
    raise HTTPException(500)

if __name__ == "__main__":
    app.run()
```

## Development Setup

To set up a development environment for Nebula:

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/VxidDev/nebula.git
    cd nebula
    ```
2.  **Create and activate a virtual environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use venv\Scripts\activate\
    ```
3.  **Install Nebula**:
    Nebula can be installed in editable mode for development.

    ```bash
    pip install -e .
    ```

## Testing

Nebula uses `pytest` for its test suite. To run the tests:

1.  Ensure you have activated the virtual environment and installed the development dependencies.
2.  Run the following command in the project's root directory:
    ```bash
    pytest
    ```
    This will discover and run all tests located in the `tests/` directory. For asynchronous tests, ensure `pytest-asyncio` is installed.