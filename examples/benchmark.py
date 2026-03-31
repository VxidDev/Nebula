from nebula import Nebula , run_prod

app = Nebula("127.0.0.1", 5000)
app.set_import_string("app") # needed for more workers to work

@app.get("/")
async def home():
    return {"test": "test"} # will be auto-detected. A bit slower, yet cleaner.

if __name__ == "__main__":
    run_prod(app, workers=4, access_log=False)