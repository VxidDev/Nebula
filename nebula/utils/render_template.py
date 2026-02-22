from jinja2 import Environment , FileSystemLoader , Template
from werkzeug import Response

class TemplateRendererError(BaseException):
    pass

def init_template_renderer(app) -> None:
    app.jinja_env = Environment(loader=FileSystemLoader(app.templates_dir))
    return

def render_template(app, filename: str, **kwargs) -> Response:
    if not app.jinja_env:
        raise TemplateRendererError("Template renderer not initialized.") 

    template: Template = app.jinja_env.get_template(filename)
    template: str = template.render(**kwargs)

    return Response(template , 200 , headers={"Content-Type": "text/html"})

def render_template_string(app, template_string: str, **kwargs) -> str:
    if not app.jinja_env: 
        raise TemplateRendererError("Template renderer not initialized.") 

    template: Template = Template(template_string)
    return template.render(**kwargs)