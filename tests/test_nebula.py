import pytest
import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Union

from nebula.server import Nebula
from nebula.request import Request
from nebula.response import PlainTextResponse, HTMLResponse, JSONResponse, RedirectResponse
from nebula.session import SecureCookieSessionManager, UserMixin
from nebula.exceptions import InvalidMethod, DuplicateEndpoint, TemplateNotFound

# ---------- Helper ASGI Test Client ----------

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
            "root_path": "",
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
    _app = Nebula(__name__, debug=True, host="127.0.0.1", port=8000)
    _app.init_all()
    return _app

@pytest.fixture
def client(app):
    return ASGITestClient(app)


# ---------- Tests ----------

@pytest.mark.asyncio
async def test_simple_get(app, client):
    @app.route("/hello")
    async def hello(req: Request):
        return PlainTextResponse("Hello!")

    resp = await client.get("/hello")
    assert resp.status_code==200
    assert resp.text=="Hello!"

@pytest.mark.asyncio
async def test_post_route(app, client):
    @app.route("/post_test", methods=["POST"])
    async def post_test(req: Request):
        return PlainTextResponse("POST OK")

    resp = await client.post("/post_test", data="abc")
    assert resp.status_code==200
    assert resp.text=="POST OK"

@pytest.mark.asyncio
async def test_404(app, client):
    resp = await client.get("/notfound")
    assert resp.status_code==404
    assert app.NOT_FOUND.encode() in resp.body

@pytest.mark.asyncio
async def test_method_not_allowed(app, client):
    @app.route("/only_get")
    async def only_get(req: Request):
        return PlainTextResponse("GET OK")

    resp = await client.post("/only_get", data="x")
    assert resp.status_code==405
    assert app.METHOD_NOT_ALLOWED.encode() in resp.body

@pytest.mark.asyncio
async def test_500_handler(app, client):
    @app.route("/error")
    async def error(req: Request):
        raise Exception("Boom!")

    resp = await client.get("/error")
    assert resp.status_code==500
    assert app.INTERNAL_ERROR.encode() in resp.body

@pytest.mark.asyncio
async def test_template_rendering(app, client):
    temp_dir = tempfile.mkdtemp()
    app.templates_dir = Path(temp_dir)
    from nebula.utils import init_template_renderer
    init_template_renderer(app)

    template_file = Path(temp_dir)/"hello.html"
    template_file.write_text("<h1>Hello {{ name }}</h1>")

    @app.route("/tpl")
    async def tpl(req: Request):
        return await app.render_template("hello.html", name="Test")

    resp = await client.get("/tpl")
    assert resp.status_code==200
    assert "Hello Test" in resp.text

    shutil.rmtree(temp_dir)

@pytest.mark.asyncio
async def test_json_response(app, client):
    @app.route("/json")
    async def json_route(req: Request):
        return JSONResponse({"ok": True})

    resp: JSONResponse = await client.get("/json")
    assert resp.status_code==200
    assert resp.json()=={"ok": True}
    assert resp.media_type=="application/json"

@pytest.mark.asyncio
async def test_redirect_response(app, client):
    @app.route("/redir")
    async def redir(req: Request):
        return RedirectResponse("/target")

    resp = await client.get("/redir")
    assert resp.status_code in (302, 307)

@pytest.mark.asyncio
async def test_session_set_get(app, client):
    app.setup_sessions("secret123")

    @app.route("/set")
    async def set_route(req: Request):
        req.session["x"]="y"
        return PlainTextResponse("ok")

    @app.route("/get")
    async def get_route(req: Request):
        return PlainTextResponse(req.session.get("x","none"))

    # set session
    resp1 = await client.get("/set")
    cookie = resp1.headers.get("set-cookie")
    assert "nebula_session" in cookie

    # extract session cookie
    cookie_val = cookie.split(";")[0].split("=")[1]

    # get session
    resp2 = await client.get("/get", cookies={"nebula_session": cookie_val})
    assert resp2.status_code==200
    assert "y" in resp2.text