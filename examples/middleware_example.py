from nebula import Nebula
from nebula.middleware import Middleware, BaseMiddleware
import datetime

class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            start_time = datetime.datetime.now()
            print(f"[{start_time}] Request started for {scope['path']}")

            await super().__call__(scope, receive, send)

            end_time = datetime.datetime.now()
            duration = end_time - start_time
            print(f"[{end_time}] Request finished for {scope['path']} in {duration.total_seconds():.4f} seconds")
        else:
            await super().__call__(scope, receive, send)

class APILoggerMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            start_time = datetime.datetime.now()
            print(f"[{start_time}] Handling API request... {scope['path']}")

            await super().__call__(scope, receive, send)
        else:
            await super().__call__(scope, receive, send)

app = Nebula(
    middlewares = [
        Middleware(LoggingMiddleware)
    ]
)

api = app.group(
    "/api",
    middlewares = [
        Middleware(APILoggerMiddleware)
    ]
)

@app.get("/")
async def home():
    return "<h1>Hello from Nebula with Logging Middleware!</h1>"

@api.get("/greet/{name}")
async def greet(name: str):
    return {"greeting": f"Hi, {name}!"}

if __name__ == "__main__":
    app.run()