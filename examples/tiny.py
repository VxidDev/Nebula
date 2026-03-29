from nebula import Nebula
from nebula.response import HTMLResponse

app = Nebula(__file__, "localhost", 8000)

@app.get("/")
async def root() -> None:
    return "<h1>Welcome to Nebula!</h1>"

if __name__ == "__main__":
    app.run()