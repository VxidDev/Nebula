from typing import Optional
from pathlib import Path 
from jinja2 import Environment , FileSystemLoader
from ..response import Response, HTMLResponse
from ..types import DEFAULT_404_BODY
import mimetypes

def init_static_serving(app, endpoint: str = "static", static_dir: Optional[str] = None) -> None:
    if static_dir:
        resolved_static_dir = Path(static_dir)
        if not resolved_static_dir.is_absolute():
            resolved_static_dir = Path(app.module_name).resolve().parent / resolved_static_dir
    else:
        resolved_static_dir = Path(app.module_name).resolve().parent / "statics"
    app.statics_dir = resolved_static_dir
        
    import mimetypes

    @app.route(f"/{endpoint}/" + "{path}")
    async def serve_file(request, path):
        file_path = app.statics_dir / path

        if not file_path.exists() or not file_path.is_file():
            return HTMLResponse(DEFAULT_404_BODY, status_code=404)

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        mime_type = mime_type or "application/octet-stream"  # fallback

        # Read file content
        with open(file_path, "rb") as f:  # read as bytes
            content = f.read()

        # Return response with Content-Type
        return Response(content, media_type=mime_type)

    return 

def init_template_path(app , template_dir: Optional[str] = None) -> None:
    app.templates_dir = Path(app.module_name).resolve().parent / ("templates" if not template_dir else template_dir) # Path / (templates_dir OR "templates")
    return  

def init_template_renderer(app) -> None:
    app.jinja_env = Environment(loader=FileSystemLoader(app.templates_dir), enable_async=True)
    return  

def init_template_renderer_sync(app) -> None:
    app.jinja_env_sync = Environment(loader=FileSystemLoader(app.templates_dir), enable_async=False)
    return