from werkzeug.utils import send_file
from typing import Optional

def init_static_serving(app, endpoint: str = "static", static_dir: Optional[str] = None):
    if not static_dir:
        static_dir = app.statics_dir
        
    @app.route(f"/{endpoint}/<path>")
    def serve_file(request, path):
        return send_file(static_dir / path , request.environ)