import pytest
import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Union, Callable

from nebula.server import Nebula, get_request, has_request
from nebula import current_app # Added current_app import
from nebula.types import DEFAULT_404_BODY
from nebula.routing import RouteGroup
from nebula.request import Request
from nebula.response import PlainTextResponse, HTMLResponse, JSONResponse, RedirectResponse, Response 
from nebula.session import SecureCookieSessionManager, UserMixin
from nebula.exceptions import InvalidMethod, DuplicateEndpoint, TemplateNotFound, InvalidResponseClass, HTTPException
from nebula.utils.htmlify import htmlify
from nebula.utils.initializers import init_static_serving, init_template_renderer, init_template_renderer_sync
from nebula.utils.jsonify import jsonify
from nebula.utils.load_template import load_template
from nebula.utils.render_template import (
    _get_template, TemplateRendererError,
    _get_template_string, render_template_async, render_template,
    render_template_string_async, render_template_string
)
from nebula.cache import cache, cached


# ---------- Helper ASGI Test Client ----------

class ASGIResponse:
    def __init__(self, status_code: int, headers, body: bytes):
        self.status_code = status_code
        self.headers = {k.decode().lower(): v.decode() for k, v in headers}
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
    _app = Nebula(debug=True, host="127.0.0.1", port=8000, make_current=False)
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

@pytest.mark.asyncio
async def test_is_html_auto_detected(app, client):
    @app.route("/html")
    async def html():
        return "<h1>Hello!<h1>"

    resp = await client.get("/html")
    assert resp.status_code == 200
    assert resp.media_type == "text/html"

@pytest.mark.asyncio
async def test_is_json_auto_detected(app, client):
    @app.route("/json")
    async def json():
        return {"json": "test"}

    resp = await client.get("/json")
    assert resp.status_code == 200
    assert resp.media_type == "application/json"

@pytest.mark.asyncio
async def test_is_redirect_auto_detected(app, client):
    @app.route("/redirect")
    async def redirect():
        return f"http://{app.host}:{app.port}/html" 

    resp = await client.get("/redirect")
    assert resp.status_code == 302
    assert resp.headers["location"] == f"http://{app.host}:{app.port}/html" 

@pytest.mark.asyncio
async def test_is_plain_text_auto_detected(app, client):
    @app.route("/plain")
    async def plain():
        return "hi" 

    resp = await client.get("/plain")
    assert resp.status_code == 200
    assert resp.body == b"hi"

@pytest.mark.asyncio
async def test_is_html_return_type_correctly_auto_detected(app, client):
    @app.route("/html-or-json", return_class=HTMLResponse)
    async def htmlOrJson() -> JSONResponse:
        return "hi" 

    resp = await client.get("/html-or-json")
    assert resp.status_code == 200
    assert resp.media_type == "text/html"

@pytest.mark.asyncio
async def test_is_json_return_type_correctly_auto_detected(app, client):
    @app.route("/json-resp")
    async def jsonResp() -> JSONResponse:
        return {"greeting": "hi"} 

    resp = await client.get("/json-resp")
    assert resp.status_code == 200
    assert resp.media_type == "application/json"
    assert resp.body == b'{"greeting":"hi"}'

@pytest.mark.asyncio
async def test_is_none_return_type_handled_correctly(app, client):
    @app.route("/none-resp")
    async def noneReturnType() -> None:
        return "hi" 

    @app.route("/none-response", return_class=None)
    async def noneRespType():
        return "hi"

    resp = await client.get("/none-resp")
    assert resp.status_code == 200
    assert resp.media_type == "text/plain"

    resp = await client.get("/none-response")
    assert resp.status_code == 200
    assert resp.media_type == "text/plain"

@pytest.mark.asyncio
async def test_is_invalid_return_type_handled_correctly(app, client):
    try:
        @app.route("/int-resp")
        async def intRes() -> int:
            return "hi"

        raise RuntimeError("[INVALID] int response passed the check.") 
    except InvalidResponseClass:
        pass 

    try:
        @app.route("/str-resp")
        async def strRes() -> str:
            return "hi"

        raise RuntimeError("[INVALID] str response passed the check.") 
    except InvalidResponseClass:
        pass
    
    try:
        @app.route("/tuple-resp")
        async def tupleRes() -> tuple:
            return "hi"

        raise RuntimeError("[INVALID] tuple response passed the check.") 
    except InvalidResponseClass:
        pass
    
    try:
        @app.route("/list-resp")
        async def listRes() -> list:
            return "hi"

        raise RuntimeError("[INVALID] list response passed the check.") 
    except InvalidResponseClass:
        pass

@pytest.mark.asyncio
async def test_is_route_group_working(app, client):
    api: RouteGroup = client.app.group("/api")

    @api.get("/greet/{name}")
    async def jsonResp(name) -> JSONResponse:
        return {"greeting": f"Hi, {name}!"}

    @api.post("/add")
    async def evalApi(request: Request):
        json = await request.json()
        x, y = json.get("x", None), json.get("y", None)

        return {"result": x + y} 

    resp = await client.get("/api/greet/Anon")
    assert resp.status_code == 200
    assert resp.media_type == "application/json"
    assert resp.body == b'{"greeting":"Hi, Anon!"}'

    resp = await client.post("/api/add", json={"x": 5, "y": 6})
    assert resp.status_code == 200
    assert resp.media_type == "application/json"
    assert resp.body == b'{"result":11}'

@pytest.mark.asyncio
async def test_are_HTTPExceptions_handled_correctly(app, client):
    @app.route("/404")
    async def raise404():
        raise HTTPException(404)

    resp = await client.get("/404")
    assert resp.status_code == 404
    assert resp.media_type == "text/html"
    assert resp.body == DEFAULT_404_BODY.encode()

# New test for custom error handler with request object
@pytest.mark.asyncio
async def test_custom_error_handler_with_request(app, client):
    # Define a custom error handler that uses the request object
    custom_error_message = "Custom Error: Path was {}"

    @app.error_handler(400) # Register for Bad Request
    async def custom_400_handler(scope: dict, receive: Callable, send: Callable, request: Request):
        error_path = request.path # Accessing the request object
        return HTMLResponse(custom_error_message.format(error_path), status_code=400)

    # Define a route that will raise a 400 error
    @app.route("/trigger_400")
    async def trigger_400(req: Request):
        # Simulate a condition that raises a 400 error, e.g., invalid input
        raise HTTPException(400)

    # Make a request to trigger the 400 error
    resp = await client.get("/trigger_400")

    # Assertions
    assert resp.status_code == 400
    assert custom_error_message.format("/trigger_400").encode() in resp.body
    assert "Custom Error: Path was /trigger_400" in resp.text

    # Test that default handlers still work if not overridden (implicitly tested by other tests)

@pytest.mark.asyncio
async def test_cached_route_lookup(app, client):
    # Ensure cache is clear before test
    cache.clear()
    assert len(cache._cache) == 0

    @app.route("/cached_user/{user_id}")
    async def cached_user_route(req: Request, user_id: str):
        return PlainTextResponse(f"User ID: {user_id}")

    # First request: should populate cache
    resp1 = await client.get("/cached_user/123")
    assert resp1.status_code == 200
    assert resp1.text == "User ID: 123"

    # Check if the cache contains the lookup result for this path/method
    # The key format is "module:function:instance:arg1:arg2:..."
    # We need to be flexible about the instance part due to changing memory addresses.
    expected_module_func_prefix = "nebula.server:_lookup_route"
    expected_path_part = "/cached_user/123"
    expected_method_part = "GET"

    found_in_cache = False
    for key in cache._cache.keys():
        if key.startswith(expected_module_func_prefix) and \
           expected_path_part in key and \
           expected_method_part in key: # This check might be too broad, but will catch the method.
           # A more precise check would involve parsing the key. For now, this should suffice.
            found_in_cache = True
            break
    assert found_in_cache, "Route lookup result should be in cache after first request"
    
    # Second request: should hit cache
    resp2 = await client.get("/cached_user/123")
    assert resp2.status_code == 200
    assert resp2.text == "User ID: 123"

    # Test with a different user_id (new cache entry)
    resp3 = await client.get("/cached_user/456")
    assert resp3.status_code == 200
    assert resp3.text == "User ID: 456"

    expected_path_part_2 = "/cached_user/456"
    found_in_cache_2 = False
    for key in cache._cache.keys():
        if key.startswith(expected_module_func_prefix) and \
           expected_path_part_2 in key and \
           expected_method_part in key:
            found_in_cache_2 = True
            break
    assert found_in_cache_2, "Second route lookup result should be in cache"

    # Verify that clearing the cache works
    cache.clear()
    assert len(cache._cache) == 0

    # After clearing, a new request should re-populate the cache
    resp4 = await client.get("/cached_user/789")
    assert resp4.status_code == 200
    assert resp4.text == "User ID: 789"

    expected_path_part_3 = "/cached_user/789"
    found_in_cache_3 = False
    for key in cache._cache.keys():
        if key.startswith(expected_module_func_prefix) and \
           expected_path_part_3 in key and \
           expected_method_part in key:
            found_in_cache_3 = True
            break
    assert found_in_cache_3, "Cache should be re-populated after clear"

import time

@pytest.mark.asyncio
async def test_cached_ttl_expiration():
    cache.clear()
    
    call_count_with_ttl = 0
    @cached(ttl=1)
    def function_with_ttl():
        nonlocal call_count_with_ttl
        call_count_with_ttl += 1
        return f"Value with TTL {call_count_with_ttl}"
    
    # Test with TTL
    assert function_with_ttl() == "Value with TTL 1"
    assert function_with_ttl() == "Value with TTL 1" # Should be cached

    # Wait for TTL to expire
    time.sleep(1.1)

    assert function_with_ttl() == "Value with TTL 2" # Should have expired and re-cached
    assert function_with_ttl() == "Value with TTL 2" # Should be cached again

    cache.clear()

    call_count_no_ttl = 0
    @cached(ttl=None)
    def function_no_ttl():
        nonlocal call_count_no_ttl
        call_count_no_ttl += 1
        return f"Value with no TTL {call_count_no_ttl}"
    
    # Test without TTL
    assert function_no_ttl() == "Value with no TTL 1"
    assert function_no_ttl() == "Value with no TTL 1" # Should be cached

    # Wait longer than a potential TTL (should not matter)
    time.sleep(0.5)

    assert function_no_ttl() == "Value with no TTL 1" # Should still be cached (no expiration)
    
    # Ensure cache still holds the value even after more time
    time.sleep(0.7) # Total sleep > 1.1
    assert function_no_ttl() == "Value with no TTL 1"

@pytest.mark.asyncio
async def test_current_app_attributes():
    app = Nebula(debug=False, host="1.2.3.4", port=1234)
    app.setting_test = "test_value"

    with app.test_context():
        assert current_app.debug is False
        assert current_app.host == "1.2.3.4"
        assert current_app.port == 1234
        assert current_app.setting_test == "test_value"

@pytest.mark.asyncio
async def test_sync_json(capsys, app, client):
    @app.get("/")
    def root(req: Request):
        return req.json_sync()

    await client.get("/")
    captured = capsys.readouterr()

    assert captured.out == "\033[1;31mERROR:\033[1;0m Request body not loaded. Use 'await request.json()' or preload it via middleware.\n" 





