from nebula import Nebula, run_dev
from nebula.response import Response, JSONResponse, HTMLResponse

from nebula.utils import (
    jsonify, htmlify, load_template , render_template_async , render_template_string_async
)

app = Nebula(__file__ , "localhost", 8000, False)
app.init_all("statics")

jinja_template = """
    <h1>{{ APP.host + ":" + APP.port|string }}</h1>
"""

@app.route("/" , methods=["GET" , "POST"])
async def main(request):
    if request.method == "POST":    
        data = await request.json()
        return jsonify({"greet": f"Hi, {data.get('name', 'default')}!"})

    return await render_template_async(app, "test.html")

@app.get("/greet/{name}")
def greet(request, name):
    return htmlify(f"<h1>Hi, {name}!</h1>")

@app.route("/fruits", return_class=JSONResponse)
def jsonTest(request):
    return {
        "fruits": {
            "apples": 6,
            "pears": 10,
            "mangos": 9
        } 
    }

@app.error_handler(405)
async def method_not_allowed(scope, receive, send):
    await htmlify("<h1>Cant do that :[</h1>", 405)(scope, receive, send)

@app.error_handler(404)
async def not_found(scope, receive, send):
    await htmlify("<h1>Cant find that :(</h1>", 404)(scope, receive, send)

@app.error_handler(500)
async def doesnt_work(scope, receive, send):
    await htmlify("<h1>Internal Error!</h1>", 500)(scope, receive, send)

@app.route("/internal-error")
async def error(request):
    await Response(f"Error!", 500)

@app.post("/api")
async def api(request):
    json = await request.json()
    return str({"a": 1, "b": 2, "c": 3}[json.get("item", "a")]) # PlainTextResponse

@app.route("/jinja")
async def jinja(request):
    return await render_template_async(app, "jinja_template.html", APP=app)

@app.route("/jinja/string", return_class=HTMLResponse)
async def jinja_string(request):
    string = await render_template_string_async(app, jinja_template, APP=app)
    return string

if __name__ == "__main__":
    run_dev(app, "localhost", 8000)
