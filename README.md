# Nebula

**Nebula** is a lightweight Python backend framework with middleware and routing, built on top of the standard `http.server` module. It allows you to create web applications quickly with simple, decorator-based routing.

## Features

-   **Lightweight**: Built on Python's standard library with no external dependencies.
-   **Decorator-based Routing**: Define your routes with simple and intuitive decorators.
-   **Template Loading**: Easily load and serve HTML templates from a designated directory.
-   **Easy to Use**: Get a server up and running in just a few lines of code.

## Installation

Since Nebula is self-contained and has no external dependencies, you can clone this repository to get started:

```bash
git clone https://github.com/your-username/nebula.git
cd nebula

pip install .
```

## Usage

Here's a basic example of how to create a simple web server with Nebula.

First, create your main application file (e.g., `main.py`):

```python
from nebula import Nebula , Response , jsonify
from pathlib import Path 

app = Nebula("localhost", 8000, True)
app.templates_dir = Path(__file__).resolve().parent / "templates"

@app.before_request
def func(request):
    print(f"received request on {request.route.path} with method {request.method}...")

@app.after_request
def func(request):
    print(f"successfully handled request on {request.route.path} with method {request.method}...")

@app.internal_error_handler
def internal_error():
    return Response('<h1 style="font-size: 100px;">something doesnt work.</h1>', 500)

@app.route("/")
def main():
    return Response(app.load_template("index.html"), 200)

@app.route("/fruits")
def jsonTest():
    return jsonify({
        "fruits": {
            "apples": 6,
            "pears": 10,
            "mangos": 9
        } 
    })

app.run()
```

Next, create a `templates` directory and add an `index.html` file inside it:

`templates/index.html`:
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

Now, you can run your application:

```bash
python main.py
```

Open your browser and navigate to `http://localhost:8000` to see your page.

## License

This project is licensed under the terms of the LICENSE file.
