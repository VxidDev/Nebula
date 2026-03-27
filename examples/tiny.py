from nebula import Nebula , run_dev
from nebula.utils import htmlify

app = Nebula(__file__, "localhost", 8000)

@app.route("/")
async def root(request) -> None:
    return htmlify("<h1>Welcome to Nebula!</h1>")

run_dev(app)