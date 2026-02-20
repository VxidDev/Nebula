# Nebula

**Nebula** is a lightweight and easy-to-use HTTP server for Python, built on top of the standard `http.server` module. It allows you to create web applications quickly with simple, decorator-based routing.

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
from nebula import Nebula
from pathlib import Path

# Initialize the application
app = Nebula("localhost", 8000)

# Set the directory for your templates
app.templates_dir = Path(__file__).resolve().parent / "templates"

# Define a route for the root URL
@app.route("/")
def main():
    # Load and return an HTML template
    return app.load_template("index.html"), 200

# Run the server
if __name__ == "__main__":
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
