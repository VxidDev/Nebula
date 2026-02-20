from nebula import Nebula
from pathlib import Path 

app = Nebula("localhost", 8000)
app.templates_dir = Path(__file__).resolve().parent / "templates"

@app.route("/")
def main():
    return app.load_template("test.html"), 200

app.run()