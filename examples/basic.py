from nebula import Nebula , Response, current_request

from nebula.utils import (
    jsonify, htmlify, init_static_serving , load_template , render_template , init_template_renderer , render_template_string,
    init_template_path
)

app = Nebula(__file__ , "localhost", 8000, False)

init_static_serving(app, "statics")
init_template_path(app)
init_template_renderer(app)

jinja_template = """
    <h1>{{ APP.host + ":" + APP.port|string }}</h1>
"""

@app.route("/" , methods=["GET" , "POST"])
def main():
    if current_request.method == "POST":    
        data = current_request.get_json()

        return jsonify({"greet": f"Hi, {data.get('name', 'default')}!"})

    return render_template(app, "test.html")

@app.route("/greet/<name>")
def greet(name):
    return htmlify(f"<h1>Hi, {name}!</h1>")

@app.route("/fruits")
def jsonTest():
    return jsonify({
        "fruits": {
            "apples": 6,
            "pears": 10,
            "mangos": 9
        } 
    })

@app.error_handler(405)
def method_not_allowed():
    return htmlify("<h1>Cant do that :[</h1>", 405)

@app.error_handler(404)
def not_found():
    return htmlify("<h1>Cant find that :(</h1>", 404)

@app.error_handler(500)
def doesnt_work():
    return htmlify("<h1>Internal Error!</h1>", 500)

@app.route("/internal-error")
def error():
    return Response(f"Error!", 500)

@app.route("/api", methods=["POST"])
def api():
    return jsonify({"a": 1, "b": 2, "c": 3}[current_request.get_json().get("item", "a")])

@app.route("/jinja")
def jinja():
    return render_template(app, "jinja_template.html", APP=app)

@app.route("/jinja/string")
def jinja_string():
    return htmlify(render_template_string(app, jinja_template, APP=app))

app.run()