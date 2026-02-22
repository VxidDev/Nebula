# Nebula

[![PyPI](https://img.shields.io/pypi/v/nebula-core?style=flat-square)](https://pypi.org/project/nebula-core/)
[![Stars](https://img.shields.io/github/stars/VxidDev/nebula?style=flat-square)](https://github.com/VxidDev/nebula/stargazers)
[![Contributors](https://img.shields.io/github/contributors/VxidDev/nebula?style=flat-square)](https://github.com/VxidDev/nebula/graphs/contributors)

**Nebula** is a lightweight Python backend framework with middleware and routing, built on top of the `werkzeug` module. It allows you to create web applications quickly with simple, decorator-based routing.

## Features

- **Decorator-based Routing**: Define your routes with simple and intuitive decorators.
- **Template Loading**: Easily load and serve HTML templates from a designated directory.
- **Statics Loading**: Easily load and serve files from designated directory.
- **Middleware Support**: `before_request` and `after_request` hooks for flexible request handling.
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
from werkzeug.wrappers import Response

from nebula import Nebula 
from nebula.utils import jsonify, init_static_serving
from pathlib import Path 

app = Nebula("localhost", 8000, False)
app.templates_dir = Path(__file__).resolve().parent / "templates"
app.statics_dir = Path(__file__).resolve().parent / "statics"

init_static_serving(app, "statics")

@app.route("/" , methods=["GET" , "POST"])
def main(request):
    if request.method == "POST":    
        data = request.get_json()

        return jsonify({"greet": f"Hi, {data.get('name', 'default')}!"})

    return Response(app.load_template("test.html"), 200, content_type="text/html")

@app.route("/greet/<name>")
def greet(request, name):
    return Response(f"Hi, {name}!", 200)

@app.route("/fruits")
def jsonTest(request):
    return jsonify({
        "fruits": {
            "apples": 6,
            "pears": 10,
            "mangos": 9
        } 
    })

@app.error_handler(405)
def method_not_allowed(request):
    return Response("Cant do that :[", 405)

@app.error_handler(404)
def not_found(request):
    return Response("Cant find that :(", 404)

@app.route("/internal-error")
def error(request):
    return Response(f"Error!", 500)

@app.route("/api", methods=["POST"])
def api(request):
    return jsonify({"a": 1, "b": 2, "c": 3}[request.get_json().get("item", "a")])

app.run()
```

**templates/index.html**:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Hello from Nebula!</title>
</head>
<body>
    <h1>Welcome to Nebula</h1>
    <p>This is a page served by the Nebula web server.</p>
</body>
</html>
```

**Run your app**:
```bash
python main.py
```

Open your browser and navigate to `http://localhost:8000` to see your page.

## Contributions <3
**amogus-gggy** - refactoring Nebula 0.2.0. Huge thank you!

## License

This project is licensed under the MIT License - see the LICENSE file for details.
