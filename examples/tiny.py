from nebula import Nebula , run_dev
from nebula.response import HTMLResponse

app = Nebula(__file__, "localhost", 8000)

@app.get("/", return_class=HTMLResponse)
async def root(request) -> None:
    return "<h1>Welcome to Nebula!</h1>"

run_dev(app)