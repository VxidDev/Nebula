from typing import Optional
from pathlib import Path 
from jinja2 import Environment , FileSystemLoader
from ..response import Response, HTMLResponse
from ..types import DEFAULT_404_BODY
import mimetypes

def init_static_serving(app, endpoint: str = "static", static_dir: Optional[str] = None) -> None:
    app.statics_dir = Path(app.module_name).resolve().parent / (static_dir if static_dir else "statics") 
        
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