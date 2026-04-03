from nebula import Nebula
from nebula.response import Response, HTMLResponse
from nebula.exceptions import HTTPException

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

    return await app.render_template_async("test.html")

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
async def method_not_allowed():
    return "<h1>Cant do that :[</h1>"

@app.error_handler(404)
async def not_found():
    return "<h1>Cant find that :(</h1>"

@app.error_handler(500)
async def doesnt_work():
    return "<h1>Internal Error!</h1>"

@app.get("/internal-error")
async def error():
    raise HTTPException(500)

@app.post("/api")
async def api(request):
    json = await request.json()
    return {"a": 1, "b": 2, "c": 3}[json.get("item", "a")] # PlainTextResponse

@app.get("/jinja")
async def jinja():
    return await app.render_template_async("jinja_template.html", APP=app)

@app.get("/jinja/string")
async def jinja_string():
    return await app.render_template_string_async(jinja_template, APP=app) 

if __name__ == "__main__":
    app.run("localhost", 8000)
