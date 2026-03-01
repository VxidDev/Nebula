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
- **Flexible Error Handling**: Easily handle HTTP errors with use of `error_handler(<http_code)`.
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
from nebula import Nebula , Response, current_request

from nebula.utils import (
    jsonify, htmlify, load_template , render_template , render_template_string
)

app = Nebula(__file__ , "localhost", 8000, False)

app.init_all("statics")

jinja_template = """
    <h1>{{ APP.host + ":" + APP.port|string }}</h1>
"""

@app.route("/" , methods=["GET" , "POST"])
def main():
    if current_request.method == "POST":    
        data = current_request.get_json()

        return jsonify({"greet": f"Hi, {data.get('name', 'default')}!"})

    return render_template(app, "test.html")

@app.route("/greet/<name>")
def greet(name):
    return htmlify(f"<h1>Hi, {name}!</h1>")

@app.route("/fruits")
def jsonTest():
    return jsonify({
        "fruits": {
            "apples": 6,
            "pears": 10,
            "mangos": 9
        } 
    })

@app.error_handler(405)
def method_not_allowed():
    return htmlify("<h1>Cant do that :[</h1>", 405)

@app.error_handler(404)
def not_found():
    return htmlify("<h1>Cant find that :(</h1>", 404)

@app.error_handler(500)
def doesnt_work():
    return htmlify("<h1>Internal Error!</h1>", 500)

@app.route("/internal-error")
def error():
    return Response(f"Error!", 500)

@app.route("/api", methods=["POST"])
def api():
    return jsonify({"a": 1, "b": 2, "c": 3}[current_request.get_json().get("item", "a")])

@app.route("/jinja")
def jinja():
    return render_template(app, "jinja_template.html", APP=app)

@app.route("/jinja/string")
def jinja_string():
    return htmlify(render_template_string(app, jinja_template, APP=app))

app.run()
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
Huge thank you!

## License

This project is licensed under the MIT License - see the LICENSE file for details.
