
from nebula import Nebula, request
from nebula.exceptions import HTTPException

app = Nebula()
app.init_all("statics")

jinja_template = """
    <h1>{{ APP.host + ":" + APP.port|string }}</h1>
"""

@app.route("/" , methods=["GET" , "POST"])
async def main():
    if request.method == "POST":    
        data = await request.json()
        name = data.get("name", "default")
        
        return {"greet": f"Hi, {name}!"}

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
async def api():
    body = await request.json()
    data = {"a": 1, "b": 2, "c": 3}
    return data.get(body.get("item"), data["a"]) # PlainTextResponse

@app.get("/jinja/{mode}")
async def jinja(mode: str = "file"):
    if mode == "string":
        return await app.render_template_string_async(jinja_template, APP=app)
        
    return await app.render_template_async("jinja_template.html", APP=app)

if __name__ == "__main__":
    app.run("localhost", 8000)
