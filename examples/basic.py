from nebula import Nebula , Response
from pathlib import Path 

app = Nebula("localhost", 8000, True)
app.templates_dir = Path(__file__).resolve().parent / "templates"

@app.before_request
def func(request):
    print(f"received request on {request.route.path} with method {request.method}...")

@app.after_request
def func(request):
    print(f"successfully handled request on {request.route.path} with method {request.method}...")

@app.route("/")
def main():
    return Response(app.load_template("test.html"), 200)

app.run()