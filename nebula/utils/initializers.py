from werkzeug.utils import send_file
from typing import Optional
from pathlib import Path 
from jinja2 import Environment , FileSystemLoader

def init_static_serving(app, endpoint: str = "static", static_dir: Optional[str] = None) -> None:
    app.statics_dir = Path(app.module_name).resolve().parent / (static_dir if static_dir else "statics") 
        
    @app.route(f"/{endpoint}/<path>")
    def serve_file(request, path):
        return send_file(app.statics_dir / path , request.environ)

    return 

def init_template_path(app , template_dir: Optional[str] = None) -> None:
    app.templates_dir = Path(app.module_name).resolve().parent / ("templates" if not template_dir else template_dir) # Path / (templates_dir OR "templates")
    return  

def init_template_renderer(app) -> None:
    app.jinja_env = Environment(loader=FileSystemLoader(app.templates_dir))
    return