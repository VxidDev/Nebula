import pytest
import asyncio
import json
from typing import Optional, Dict, Union

from nebula.server import Nebula, get_request
from nebula.routing import RouteGroup
from nebula.request import Request
from nebula.response import PlainTextResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from nebula.middleware import Middleware, BaseMiddleware

# Assuming ASGI test client is available or copied
class ASGIResponse:
    def __init__(self, status_code: int, headers, body: bytes):
        self.status_code = status_code
        self.headers = {k.decode(): v.decode() for k, v in headers}
        self.body = body
        self.text = body.decode()
    
    def json(self):
        return json.loads(self.text)

    @property
    def media_type(self):
        # Return content-type or empty string if not set
        return self.headers.get("content-type", "")

class ASGITestClient:
    def __init__(self, app: Nebula):
        self.app = app

    async def _request(self, method: str, path: str, body: Optional[Union[str, bytes, dict]]=None, headers: Optional[Dict[str,str]]=None, cookies: Optional[Dict[str,str]]=None):
        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [],
            "server": ("127.0.0.1", 80),
            "client": ("127.0.0.1", 1234),
        }

        if headers:
            for k,v in headers.items():
                scope["headers"].append((k.lower().encode(), v.encode()))
        if cookies:
            cookie_header = "; ".join([f"{k}={v}" for k,v in cookies.items()])
            scope["headers"].append((b"cookie", cookie_header.encode()))

        body_chunks = []
        if body:
            if isinstance(body, dict):
                body_bytes = json.dumps(body).encode()
                scope["headers"].append((b"content-type", b"application/json"))
            elif isinstance(body, str):
                body_bytes = body.encode()
                scope["headers"].append((b"content-type", b"text/plain"))
            else:
                body_bytes = body
            body_chunks.append(body_bytes)

        messages = []

        async def receive():
            if body_chunks:
                chunk = body_chunks.pop(0)
                return {"type": "http.request", "body": chunk, "more_body": bool(body_chunks)}
            return {"type": "http.disconnect"}

        async def send(msg):
            messages.append(msg)

        await self.app(scope, receive, send)

        status_code = 200
        response_headers = []
        body_parts = []

        for msg in messages:
            if msg["type"]=="http.response.start":
                status_code = msg["status"]
                response_headers = msg["headers"]
            elif msg["type"]=="http.response.body":
                body_parts.append(msg.get("body", b""))

        return ASGIResponse(status_code, response_headers, b"".join(body_parts))

    async def get(self, path, headers=None, cookies=None):
        return await self._request("GET", path, headers=headers, cookies=cookies)
    
    async def post(self, path, headers=None, json=None, form=None, data=None, cookies=None):
        if json: return await self._request("POST", path, body=json, headers=headers, cookies=cookies)
        if form: return await self._request("POST", path, body=form, headers=headers, cookies=cookies)
        if data: return await self._request("POST", path, body=data, headers=headers, cookies=cookies)
        return await self._request("POST", path, headers=headers, cookies=cookies)

# ---------- Fixtures ----------

@pytest.fixture
def app():
    _app = Nebula(debug=True, host="127.0.0.1", port=8000)
    _app.init_all()
    return _app

@pytest.fixture
def client(app):
    return ASGITestClient(app)

# ---------- Custom Middlewares for Testing ----------

class GlobalHeaderMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        async def send_wrapper(message):
            if message['type'] == 'http.response.start':
                message['headers'].append((b'x-global-header', b'global-value'))
            await send(message)
        await self.app(scope, receive, send_wrapper)

class GroupHeaderMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        async def send_wrapper(message):
            if message['type'] == 'http.response.start':
                message['headers'].append((b'x-group-header', b'group-value'))
            await send(message)
        await self.app(scope, receive, send_wrapper)

class RouteHeaderMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        async def send_wrapper(message):
            if message['type'] == 'http.response.start':
                message['headers'].append((b'x-route-header', b'route-value'))
            await send(message)
        await self.app(scope, receive, send_wrapper)

class OrderMiddleware(BaseMiddleware):
    def __init__(self, app, order_list, name):
        super().__init__(app)
        self.order_list = order_list
        self.name = name

    async def __call__(self, scope, receive, send):
        self.order_list.append(f"before_{self.name}")
        async def send_wrapper(message):
            if message['type'] == 'http.response.start':
                message['headers'].append((f'x-order-{self.name}'.encode(), f'value-{self.name}'.encode()))
            await send(message)
        await self.app(scope, receive, send_wrapper)
        self.order_list.append(f"after_{self.name}")


# ---------- Tests ----------

@pytest.mark.asyncio
async def test_global_middleware(app, client):
    app._middlewares.append(Middleware(GlobalHeaderMiddleware))

    @app.route("/test")
    async def test_route():
        return PlainTextResponse("OK")

    resp = await client.get("/test")
    assert resp.status_code == 200
    assert resp.headers.get('x-global-header') == 'global-value'

@pytest.mark.asyncio
async def test_route_group_middleware(app, client):
    group = app.group("/group")
    group.middleware(Middleware(GroupHeaderMiddleware))

    @group.get("/test")
    async def group_test_route():
        return PlainTextResponse("Group OK")

    resp = await client.get("/group/test")
    assert resp.status_code == 200
    assert resp.headers.get('x-group-header') == 'group-value'
    assert 'x-global-header' not in resp.headers # Ensure it's not global

@pytest.mark.asyncio
async def test_route_specific_middleware(app, client):
    @app.route("/specific", route_middlewares=[Middleware(RouteHeaderMiddleware)])
    async def specific_test_route():
        return PlainTextResponse("Specific OK")

    resp = await client.get("/specific")
    assert resp.status_code == 200
    assert resp.headers.get('x-route-header') == 'route-value'
    assert 'x-global-header' not in resp.headers # Ensure it's not global

@pytest.mark.asyncio
async def test_middleware_order_global_group_route(app, client):
    order_list = []

    # Global middleware
    app._middlewares.append(Middleware(OrderMiddleware, order_list=order_list, name="global"))

    # RouteGroup middleware
    group = app.group("/ordered")
    group.middleware(Middleware(OrderMiddleware, order_list=order_list, name="group"))

    # Route-specific middleware
    @group.get("/test", route_middlewares=[Middleware(OrderMiddleware, order_list=order_list, name="route")])
    async def ordered_test_route():
        order_list.append("handler_executed")
        return PlainTextResponse("Ordered OK")

    resp = await client.get("/ordered/test")
    assert resp.status_code == 200
    assert resp.headers.get('x-order-global') == 'value-global'
    assert resp.headers.get('x-order-group') == 'value-group'
    assert resp.headers.get('x-order-route') == 'value-route'

    expected_order = [
        "before_global",
        "before_group",
        "before_route",
        "handler_executed",
        "after_route",
        "after_group",
        "after_global",
    ]
    assert order_list == expected_order

@pytest.mark.asyncio
async def test_middleware_modify_request(app, client):
    class RequestModifierMiddleware(BaseMiddleware):
        async def __call__(self, scope, receive, send):
            request = get_request() # Get the actual request object
            request.state["modified_by_middleware"] = True
            await self.app(scope, receive, send)

    app._middlewares.append(Middleware(RequestModifierMiddleware))

    @app.route("/request_state")
    async def state_route(request: Request):
        return PlainTextResponse(str(request.state.get("modified_by_middleware", False)))

    resp = await client.get("/request_state")
    assert resp.status_code == 200
    assert resp.text == "True"

@pytest.mark.asyncio
async def test_multiple_group_middlewares(app, client):
    class GroupMiddleware1(BaseMiddleware):
        async def __call__(self, scope, receive, send):
            async def send_wrapper(message):
                if message['type'] == 'http.response.start':
                    message['headers'].append((b'x-group-1', b'val1'))
                await send(message)
            await self.app(scope, receive, send_wrapper)

    class GroupMiddleware2(BaseMiddleware):
        async def __call__(self, scope, receive, send):
            async def send_wrapper(message):
                if message['type'] == 'http.response.start':
                    message['headers'].append((b'x-group-2', b'val2'))
                await send(message)
            await self.app(scope, receive, send_wrapper)

    group = app.group("/multi-group")
    group.middleware(Middleware(GroupMiddleware1))
    group.middleware(Middleware(GroupMiddleware2))

    @group.get("/test")
    async def multi_group_test_route():
        return PlainTextResponse("Multi-Group OK")

    resp = await client.get("/multi-group/test")
    assert resp.status_code == 200
    assert resp.headers.get('x-group-1') == 'val1'
    assert resp.headers.get('x-group-2') == 'val2'