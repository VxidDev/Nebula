class BaseMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)

class Middleware:
    def __init__(self, middleware_cls: type, **options):
        self.middleware_cls = middleware_cls
        self.options = options

    def build(self, app):
        return self.middleware_cls(app, **self.options)