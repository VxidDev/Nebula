from nebula import HttpServer

app = HttpServer("localhost", 8000)

@app.route("/")
def main():
    return "Root!", 200

app.run()