from nebula import Nebula
from pathlib import Path 

app = Nebula("localhost", 8000)
app.templates_dir = Path(__file__).resolve().parent / "templates"

@app.before_request
def func(route):
    print(f"received request on {route.path}...")

@app.after_request
def func(route):
    print(f"successfully handled request on {route.path}...")

@app.route("/")
def main():
    return app.load_template("test.html"), 200

app.run()