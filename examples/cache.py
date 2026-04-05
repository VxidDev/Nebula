from nebula.cache import cached
from nebula import Nebula
from time import sleep 

app = Nebula()

@app.get("/{x}/{y}")
@cached()
def addition(x, y):
    sleep(5) # simulate computation
    return f"<h1>Result: {int(x) + int(y)}</h1>"

if __name__ == "__main__":
    app.run()