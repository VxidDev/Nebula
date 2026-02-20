# Nebula

Nebula is a lightweight and easy-to-use Python HTTP server that allows you to build web applications with decorator-based routing.

## Features

-   Lightweight and minimal dependencies
-   Decorator-based routing for clean and readable code
-   Easy to get started

## Installation

To use Nebula in your project, you can install it using pip:

```bash
pip install .
```

## Usage

Here's a basic example of how to create a "Hello, World!" application with Nebula:

```python
from nebula import HttpServer

# Create a server instance
app = HttpServer("localhost", 8000)

# Define a route using a decorator
@app.route("/")
def main():
    return "Hello, World!", 200

# Run the server
app.run()
```

You can then run this script and visit `http://localhost:8000` in your browser to see the "Hello, World!" message.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! If you have any ideas, suggestions, or bug reports, please open an issue or submit a pull request.
