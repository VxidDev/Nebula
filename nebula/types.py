from typing import Any, Dict

AVAILABLE_METHODS = ["GET", "POST"]

DEFAULT_TEMPLATES_DIR = "./templates"
DEFAULT_STATICS_DIR = "./statics"

DEFAULT_404_BODY = """
    <head><title>404 Not Found</title></head>

    <body>
        <h1>Not Found</h1>
        <p>The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.</p>
    </body>
"""

DEFAULT_500_BODY = """
    <head><title>500 Internal Server Error</title></head>

    <body>
        <h1>Internal Server Error</h1>
        <p>The server encountered an unexpected condition that prevented it from fulfilling the request.</p>
        <p>Please try again later.</p>
    </body>
"""

DEFAULT_405_BODY = """
    <head><title>405 Method Not Allowed</title></head>

    <body>
        <h1>Method Not Allowed</h1>
        <p>The requested HTTP method is not supported for this URL.</p>
    </body>
"""
