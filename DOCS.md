## Documentation

Documentation for Nebula's features.

### Middleware Support

Nebula supports middleware for processing requests and responses.

**Defining a Middleware Class**:
Middleware classes should typically inherit from `BaseMiddleware` or implement an ASGI-compatible `__call__` method.

```python
from nebula import Nebula, Request, Middleware, BaseMiddleware

# Example Middleware Class
class LogMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        print(f"Incoming request: {self.app.scope['method']} {self.app.scope['path']}")
        await self.app(scope, receive, send)
        print("Response sent.")

# Global Middleware: Passed during Nebula initialization
app = Nebula(middlewares=[Middleware(LogMiddleware)])

# Route-Specific Middleware: Applied to a group or individual route
@app.group("/admin", middlewares=[Middleware(LogMiddleware)])
def admin_group():
    @app.get("/dashboard")
    async def admin_dashboard(request: Request):
        return "Admin Dashboard"

@app.get("/users/{user_id}", route_middlewares=[Middleware(LogMiddleware)])
async def get_user(request: Request, user_id: int):
    return f"User ID: {user_id}"

if __name__ == "__main__":
    app.run()
```

### Session Management

Nebula provides secure session management using HMAC-signed cookies. You need to set a `SECRET_KEY` and call `setup_sessions`.

```python
from nebula import Nebula, Request

app = Nebula(host="localhost", port=8000)
app.setup_sessions(secret_key="your-super-secret-key-change-me") # IMPORTANT: Use a strong, unique secret key

@app.get("/session/set")
async def set_session(request: Request):
    request.session["username"] = "nebula_user"
    return "Session variable 'username' set."

@app.get("/session/get")
async def get_session(request: Request):
    username = request.session.get("username", "guest")
    return f"Hello, {username}!"

@app.get("/session/clear")
async def clear_session(request: Request):
    request.session.clear()
    return "Session cleared."

if __name__ == "__main__":
    app.run()
```

### WebSocket Support

Nebula integrates with `python-socketio` for real-time WebSocket communication.

```python
from nebula import Nebula, Request

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
    # To run, you typically need to provide the ASGI app to socketio.ASGIApp
    # In Nebula, this is handled internally via app.app which is socketio.ASGIApp(self.sio, other_asgi_app=self._core)
    # So, just running app.run() should work if Socket.IO is configured correctly.
    app.run()
```
*Note: The `app.run()` method internally handles the ASGI app composed with Socket.IO.*

### Error Handling

Define custom error handlers for specific HTTP status codes using the \`@app.error_handler()\` decorator.

```python
from nebula import Nebula, Request, HTTPException

app = Nebula()

@app.error_handler(404)
async def custom_not_found_handler(request: Request, exc: HTTPException):
    return "<h1>Oops! Page not found (404)</h1>", 404

@app.error_handler(500)
async def custom_server_error_handler(request: Request, exc: HTTPException):
    return "<h1>Something went wrong (500)</h1>", 500

@app.get("/")
async def index():
    return "Hello!"

@app.get("/raise_error")
async def raise_error():
    raise HTTPException(status_code=500, detail="This is a test internal server error.")

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
3.  **Install dependencies**:
    Nebula can be installed in editable mode for development. It's recommended to also install development dependencies.
    ```bash
    pip install -e .
    # If a requirements-dev.txt exists, install it too:
    # pip install -r requirements-dev.txt
    ```
    If `requirements-dev.txt` doesn't exist, you might need to manually install testing and other development tools (e.g., `pip install pytest pytest-asyncio`).

## Testing

Nebula uses `pytest` for its test suite. To run the tests:

1.  Ensure you have activated the virtual environment and installed the development dependencies.
2.  Run the following command in the project's root directory:
    ```bash
    pytest
    ```
    This will discover and run all tests located in the `tests/` directory. For asynchronous tests, ensure `pytest-asyncio` is installed.