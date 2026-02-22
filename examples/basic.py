from werkzeug.wrappers import Response
from werkzeug.utils import send_file
from nebula import Nebula
from nebula.utils import jsonify
from pathlib import Path 

app = Nebula("localhost", 8000, False)
app.templates_dir = Path(__file__).resolve().parent / "templates"
app.statics_dir = Path(__file__).resolve().parent / "statics"

@app.route(f"/statics/<path>")
def serve_statics(request, path):
    return send_file(app.statics_dir / path , environ=request.environ)

@app.route("/" , methods=["GET" , "POST"])
def main(request):
    if request.method == "POST":    
        data = request.get_json()

        return jsonify({"greet": f"Hi, {data.get('name', 'default')}!"})

    return Response(app.load_template("test.html"), 200, content_type="text/html")

@app.route("/<name>")
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
    return Response("Cant do that :[", 405)

@app.error_handler(404)
def not_found(request):
    return Response("Cant find that :(", 404)

@app.route("/internal-error")
def error(request):
    return Response(f"Error!", 500)

@app.route("/api", methods=["POST"])
def api(request):
    return jsonify({"a": 1, "b": 2, "c": 3})

app.run()