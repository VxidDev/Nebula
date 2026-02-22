from werkzeug.wrappers import Response

from nebula import Nebula 
from nebula.utils import jsonify, init_static_serving , load_template , render_template , init_template_renderer , render_template_string
from pathlib import Path 

app = Nebula("localhost", 8000, False)
app.templates_dir = Path(__file__).resolve().parent / "templates"
app.statics_dir = Path(__file__).resolve().parent / "statics"

init_static_serving(app, "statics")
init_template_renderer(app)

jinja_template = """
    <h1>{{ APP.host + ":" + APP.port|string }}</h1>
"""

@app.route("/" , methods=["GET" , "POST"])
def main(request):
    if request.method == "POST":    
        data = request.get_json()

        return jsonify({"greet": f"Hi, {data.get('name', 'default')}!"})

    return Response(load_template(app, "test.html"), 200, content_type="text/html")

@app.route("/greet/<name>")
def greet(request, name):
    return Response(f"Hi, {name}!", 200)

@app.route("/fruits")
def jsonTest(request):
    return jsonify({
        "fruits": {
            "apples": 6,
            "pears": 10,
            "mangos": 9
        } 
    })

@app.error_handler(405)
def method_not_allowed(request):
    return Response("<h1>Cant do that :[</h1>", 405, headers={"Content-Type": "text/html"})

@app.error_handler(404)
def not_found(request):
    return Response("<h1>Cant find that :(</h1>", 404, headers={"Content-Type": "text/html"})

@app.error_handler(500)
def doesnt_work(request):
    return Response("<h1>Internal Error!</h1>", 500, headers={"Content-Type": "text/html"})

@app.route("/internal-error")
def error(request):
    return Response(f"Error!", 500)

@app.route("/api", methods=["POST"])
def api(request):
    return jsonify({"a": 1, "b": 2, "c": 3}[request.get_json().get("item", "a")])

@app.route("/jinja")
def jinja(request):
    return render_template(app, "jinja_template.html", APP=app)

@app.route("/jinja/string")
def jinja_string(request):
    return Response(render_template_string(app, jinja_template, APP=app), 200 , headers={"Content-Type": "text/html"})

app.run()