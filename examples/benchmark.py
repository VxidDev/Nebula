from nebula import Nebula , run_prod
from nebula.response import JSONResponse

app = Nebula(__file__, "127.0.0.1", 5000)
app.set_import_string("app") # needed for more workers to work

@app.get("/", return_class=JSONResponse)
async def home(request) -> JSONResponse:
    return {"test": "test"}

if __name__ == "__main__":
    run_prod(app, workers=4)