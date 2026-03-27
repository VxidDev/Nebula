# Nebula

[![PyPI](https://img.shields.io/pypi/v/nebula-core?style=flat-square)](https://pypi.org/project/nebula-core/)
[![Stars](https://img.shields.io/github/stars/VxidDev/nebula?style=flat-square)](https://github.com/VxidDev/nebula/stargazers)
[![Contributors](https://img.shields.io/github/contributors/VxidDev/nebula?style=flat-square)](https://github.com/VxidDev/nebula/graphs/contributors)

**Nebula** is a lightweight ASGI-based Python web framework that provides simple, decorator-based routing and middleware support for building fast, asynchronous web applications.

## Features

- **Decorator-based Routing**: Define your routes with simple and intuitive decorators.
- **Asynchronous Support**: Full `async`/`await` support for handling requests and events.
- **Session Management & Authentication**: Secure session handling and user authentication.
- **WebSocket Support**: Real-time communication with WebSocket routing.
- **Template Loading**: Easily load and serve HTML templates from a designated directory.
- **Statics Loading**: Easily load and serve files from designated directory.
- **Middleware Support**: `before_request` and `after_request` hooks for flexible request handling.
- **Flexible Error Handling**: Easily handle HTTP errors with use of `error_handler(<http_code:int>)`.
- **Easy to Use**: Get a server up and running in just a few lines of code.

## Installation

Install Nebula from PyPI:

```bash
pip install nebula-core
```

or clone and install from GitHub.

```bash
git clone https://github.com/VxidDev/nebula.git
cd nebula
pip install .
```
## Usage

Here's a basic example of creating a simple web server with Nebula.

**main.py**:

```py
from nebula import Nebula , run_dev
from nebula.utils import htmlify

app = Nebula(__file__, "localhost", 8000)

@app.route("/")
async def root(request) -> None:
    return htmlify("<h1>Welcome to Nebula!</h1>")

run_dev(app) # run using uvicorn
```

**Run your app**:
```bash
python main.py
```

Open your browser and navigate to `http://localhost:8000` to see your page.

## Contributions <3
**amogus-gggy**: 
- refactoring Nebula 0.2.0.
- adding websockets support (2.0.0) <br>
- adding session support <br>

Huge thank you!

## License

This project is licensed under the MIT License - see the LICENSE file for details.
