import pytest
import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Union

from nebula.server import Nebula, get_request, has_request
from nebula.request import Request
from nebula.response import PlainTextResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from nebula.session import SecureCookieSessionManager, UserMixin
from nebula.exceptions import InvalidMethod, DuplicateEndpoint, TemplateNotFound
from nebula.utils.htmlify import htmlify
from nebula.utils.initializers import init_static_serving, init_template_renderer, init_template_renderer_sync
from nebula.utils.jsonify import jsonify
from nebula.utils.load_template import load_template
from nebula.utils.render_template import (
    _get_template, TemplateRendererError,
    _get_template_string, render_template_async, render_template,
    render_template_string_async, render_template_string
)


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
    init_template_renderer(app) # Use async renderer for this test

    template_file = Path(temp_dir)/"hello.html"
    template_file.write_text("<h1>Hello {{ name }}</h1>")

    @app.route("/tpl")
    async def tpl(req: Request):
        return await app.render_template_async("hello.html", name="Test")

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

@pytest.mark.asyncio
async def test_route_without_request_arg(app, client):
    @app.route("/no_req")
    async def no_req_handler():
        return PlainTextResponse("No request arg needed")

    resp = await client.get("/no_req")
    assert resp.status_code == 200
    assert resp.text == "No request arg needed"

@pytest.mark.asyncio
async def test_route_with_request_arg(app, client):
    @app.route("/with_req")
    async def with_req_handler(req: Request):
        return PlainTextResponse(f"Request method: {req.method}")

    resp = await client.get("/with_req")
    assert resp.status_code == 200
    assert resp.text == "Request method: GET"

@pytest.mark.asyncio
async def test_get_request_in_handler(app, client):
    @app.route("/get_req_test")
    async def get_req_test_handler():
        req = get_request()
        return PlainTextResponse(f"Path: {req.path}")

    resp = await client.get("/get_req_test")
    assert resp.status_code == 200
    assert resp.text == "Path: /get_req_test"

@pytest.mark.asyncio
async def test_has_request_in_handler(app, client):
    @app.route("/has_req_test")
    async def has_req_test_handler():
        return PlainTextResponse(str(has_request()))

    resp = await client.get("/has_req_test")
    assert resp.status_code == 200
    assert resp.text == "True"

@pytest.mark.asyncio
async def test_has_request_outside_handler():
    assert has_request() == False

@pytest.mark.asyncio
async def test_htmlify_utility(app):
    with pytest.warns(DeprecationWarning, match="htmlify utility is deprecated."):
        response = htmlify("<h1>Hello HTML!</h1>", status=201)
    assert isinstance(response, HTMLResponse)
    assert response.status_code == 201
    assert b"<h1>Hello HTML!</h1>" in response.body

@pytest.mark.asyncio
async def test_htmlify_default_status(app):
    with pytest.warns(DeprecationWarning):
        response = htmlify("<p>Default status</p>")
    assert isinstance(response, HTMLResponse)
    assert response.status_code == 200
    assert b"<p>Default status</p>" in response.body

@pytest.mark.asyncio
async def test_static_file_serving(app, client):
    temp_dir = tempfile.mkdtemp()
    static_content = b"This is a static file."
    static_file_path = Path(temp_dir) / "test.txt"
    static_file_path.write_bytes(static_content)

    init_static_serving(app, endpoint="files", static_dir=str(temp_dir)) # Register the route

    # Make a request for the static file
    resp = await client.get("/files/test.txt")
    
    assert resp.status_code == 200
    assert resp.body == static_content
    assert resp.headers.get("content-type") == "text/plain"

    shutil.rmtree(temp_dir)

@pytest.mark.asyncio
async def test_jsonify_utility(app):
    with pytest.warns(DeprecationWarning, match="jsonify utility is deprecated."):
        data = {"message": "Hello JSON!"}
        response = jsonify(data, status=201)
    assert isinstance(response, JSONResponse)
    assert response.status_code == 201
    assert json.loads(response.body) == data

@pytest.mark.asyncio
async def test_jsonify_default_status(app):
    with pytest.warns(DeprecationWarning):
        data = {"status": "ok"}
        response = jsonify(data)
    assert isinstance(response, JSONResponse)
    assert response.status_code == 200
    assert json.loads(response.body) == data

@pytest.mark.asyncio
async def test_load_template_success(app):
    temp_dir = tempfile.mkdtemp()
    app.templates_dir = Path(temp_dir)
    template_content = "Template content here."
    template_file = Path(temp_dir) / "test_load.html"
    template_file.write_text(template_content)

    loaded_content = load_template(app, "test_load.html")
    assert loaded_content == template_content
    shutil.rmtree(temp_dir)

@pytest.mark.asyncio
async def test_load_template_not_found(app):
    temp_dir = tempfile.mkdtemp()
    app.templates_dir = Path(temp_dir)

    with pytest.raises(TemplateNotFound, match="File: 'non_existent.html' not found in"):
        load_template(app, "non_existent.html")
    shutil.rmtree(temp_dir)

@pytest.mark.asyncio
async def test_get_template_no_jinja_env(app):
    app.jinja_env = None # Ensure jinja_env is not initialized
    with pytest.raises(TemplateRendererError, match="Template renderer not initialized."):
        _get_template(app, "any.html")

@pytest.mark.asyncio
async def test_get_template_string_no_jinja_env(app):
    app.jinja_env = None # Ensure jinja_env is not initialized
    with pytest.raises(TemplateRendererError, match="Template renderer not initialized."):
        _get_template_string(app, "any string")

@pytest.mark.asyncio
async def test_render_template_sync(app):
    temp_dir = tempfile.mkdtemp()
    app.templates_dir = Path(temp_dir)
    init_template_renderer_sync(app) # Reinitialize Jinja env
    template_content = "Sync Hello {{ name }}!"
    template_file = Path(temp_dir) / "sync_hello.html"
    template_file.write_text(template_content)

    response = render_template(app, "sync_hello.html", name="World")
    assert isinstance(response, HTMLResponse)
    assert response.status_code == 200
    assert b"Sync Hello World!" in response.body
    shutil.rmtree(temp_dir)

@pytest.mark.asyncio
async def test_render_template_string_async(app):
    app.templates_dir = Path(tempfile.mkdtemp()) # Ensure app.templates_dir is set before init_template_renderer
    init_template_renderer(app) # Ensure jinja_env is initialized
    template_string = "Async String Hello {{ name }}!"

    rendered_content = await render_template_string_async(app, template_string, name="Async")
    assert rendered_content == "Async String Hello Async!"
    shutil.rmtree(app.templates_dir) # Clean up temp directory

@pytest.mark.asyncio
async def test_render_template_string_sync(app):
    app.templates_dir = Path(tempfile.mkdtemp()) # Ensure app.templates_dir is set before init_template_renderer
    init_template_renderer_sync(app) # Ensure jinja_env is initialized
    template_string = "Sync String Hello {{ name }}!"

    rendered_content = render_template_string(app, template_string, name="Sync")
    assert rendered_content == "Sync String Hello Sync!"
    shutil.rmtree(app.templates_dir) # Clean up temp directory
