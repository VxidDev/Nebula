from nebula import Nebula
from nebula.utils import htmlify

app = Nebula(__file__, "localhost", 8000)

@app.route("/", endpoint="main")
def root() -> None:
    return htmlify("<h1>Welcome to Nebula!</h1>")

main = app.wsgi_app # gunicorn -w 1 -k eventlet tiny:main