from nebula import Nebula

app = Nebula()

@app.get("/")
async def root():
    return "<h1>Welcome to Nebula!</h1>"

if __name__ == "__main__":
    app.run()