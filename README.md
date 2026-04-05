# Nebula

[![PyPI](https://img.shields.io/pypi/v/nebula-core?style=flat-square)](https://pypi.org/project/nebula-core/)
[![Stars](https://img.shields.io/github/stars/VxidDev/nebula?style=flat-square)](https://github.com/VxidDev/nebula/stargazers)
[![Contributors](https://img.shields.io/github/contributors/VxidDev/nebula?style=flat-square)](https://github.com/VxidDev/nebula/graphs/contributors)

**Nebula** is a lightweight ASGI-based Python web framework that provides simple, decorator-based routing and middleware support for building fast, asynchronous web applications.

## Features

-   **Decorator-based Routing**: Define your routes with simple and intuitive decorators.
-   **Asynchronous Support**: Full `async`/`await` support for handling requests and events.
-   **Session Management**: Secure session handling using HMAC-signed cookies.
-   **WebSocket Support**: Integrated `python-socketio` for real-time communication.
-   **Template Loading**: Easily load and serve HTML templates from a designated directory using Jinja2.
-   **Statics Loading**: Easily load and serve static files from a designated directory.
-   **Middleware Support**: Chain middleware for request/response processing, both globally and per-route/group.
-   **Flexible Error Handling**: Define custom handlers for HTTP errors.
-   **Easy to Use**: Get a server up and running in just a few lines of code.

## Installation

Install Nebula from PyPI:

```bash
pip install nebula-core
```

or clone and install from GitHub:

```bash
git clone https://github.com/VxidDev/nebula.git
cd nebula
pip install .
```

## Project Structure

The Nebula project follows a standard Python project structure:

-   `.`: Root directory containing configuration files (`.gitignore`, `pyproject.toml`, `README.md`, `LICENSE`).
-   `examples/`: Example applications demonstrating various Nebula features.
-   `nebula/`: The core library code.
    -   `cache.py`: Defines cache related class and decorator (`@cached`).
    -   `middleware.py`: Defines middleware classes (`BaseMiddleware`, `Middleware`).
    -   `routing.py`: Handles route definitions (`Route`, `RouteGroup`) and path matching.
    -   `server.py`: The main ASGI application, request handling, and middleware composition logic.
    -   `request.py`: Defines the `Request` object and context.
    -   `response.py`: Defines various `Response` classes (PlainText, HTML, JSON, Redirect).
    -   `session.py`: Implements session management (`SecureCookieSessionManager`).
    -   `types.py`: Contains constants like available HTTP methods and default error messages.
    -   `exceptions.py`: Defines custom exceptions used by the framework.
    -   `utils/`: Utility functions for templating, static file serving, etc.
-   `tests/`: Contains unit and integration tests for the framework.

## Usage Examples

### Basic Routing

A simple web server with a root endpoint:

```python
from nebula import Nebula

app = Nebula()

@app.get("/")
async def root():
    return "<h1>Welcome to Nebula!</h1>"

if __name__ == "__main__":
    app.run()
```

## Contributing

Contributions are welcome! 

-   **Bug Reports**: Please report bugs in the GitHub Issues section.
-   **Feature Requests**: Feel free to open an issue to discuss new features.
-   **Pull Requests**: Fork the repository, create a new branch for your feature or bugfix, and submit a pull request. Please ensure your code follows the project's coding style and includes tests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
