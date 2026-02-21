from nebula import Nebula , Response , jsonify
from pathlib import Path 

app = Nebula("localhost", 8000, False)
app.templates_dir = Path(__file__).resolve().parent / "templates"
app.statics_dir = Path(__file__).resolve().parent / "statics"

@app.before_request
def func(request):
    print(f"received request on {request.route.path} with method {request.method}...")

@app.after_request
def func(request):
    print(f"successfully handled request on {request.route.path} with method {request.method}...")

@app.internal_error_handler
def internal_error():
    return Response('<h1 style="font-size: 100px;">something doesnt work.</h1>', 500)

@app.route("/" , methods=["GET" , "POST"])
def main():
    if app.request.method == "POST":    
        data = app.request.data.get_json()

        return jsonify({"greet": f"Hi, {data.get('name', 'default')}!"})

    return Response(app.load_template("test.html"), 200)

@app.route("/fruits")
def jsonTest():
    return jsonify({
        "fruits": {
            "apples": 6,
            "pears": 10,
            "mangos": 9
        } 
    })

app.run()