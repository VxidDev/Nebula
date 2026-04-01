from nebula import Nebula
from nebula.response import Response, HTMLResponse
from nebula.exceptions import HTTPException

from nebula.utils import (
    render_template_async , render_template_string_async
)

app = Nebula()
app.init_all("statics")

jinja_template = """
    <h1>{{ APP.host + ":" + APP.port|string }}</h1>
"""

@app.route("/" , methods=["GET" , "POST"])
async def main(request):
    if request.method == "POST":    
        data = await request.json()
        return {"greet": f"Hi, {data.get('name', 'default')}!"}

    return await render_template_async(app, "test.html")

@app.get("/greet/{name}")
def greet(name: str):
    return f"<h1>Hi, {name}!</h1>"

@app.get("/fruits")
def jsonTest():
    return {
        "fruits": {
            "apples": 6,
            "pears": 10,
            "mangos": 9
        } 
    }

@app.error_handler(405)
async def method_not_allowed(scope, receive, send):
    await HTMLResponse("<h1>Cant do that :[</h1>", 405)(scope, receive, send)

@app.error_handler(404)
async def not_found(scope, receive, send):
    await HTMLResponse("<h1>Cant find that :(</h1>", 404)(scope, receive, send)

@app.error_handler(500)
async def doesnt_work(scope, receive, send):
    await HTMLResponse("<h1>Internal Error!</h1>", 500)(scope, receive, send)

@app.get("/internal-error")
async def error():
    raise HTTPException(500)

@app.post("/api")
async def api(request):
    json = await request.json()
    return str({"a": 1, "b": 2, "c": 3}[json.get("item", "a")]) # PlainTextResponse

@app.get("/jinja")
async def jinja():
    return await render_template_async(app, "jinja_template.html", APP=app)

@app.route("/jinja/string")
async def jinja_string():
    string = await render_template_string_async(app, jinja_template, APP=app)
    return string

if __name__ == "__main__":
    app.run("localhost", 8000)
