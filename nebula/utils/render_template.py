from jinja2 import Environment , FileSystemLoader , Template
from nebula.response import HTMLResponse

class TemplateRendererError(BaseException):
    pass

def _get_template(app, filename: str) -> Template:
    if not app.jinja_env:
        raise TemplateRendererError("Template renderer not initialized.")

    template: Template = app.jinja_env.get_template(filename)
    return template

def _get_template_string(app, template_string: str) -> Template:
    if not app.jinja_env:
        raise TemplateRendererError("Template renderer not initialized.")

    template: Template = app.jinja_env.from_string(template_string)
    return template

async def render_template_async(app, filename: str, **kwargs) -> HTMLResponse:
    template = _get_template(app, filename)
    rendered_template: str = await template.render_async(**kwargs)

    return HTMLResponse(rendered_template)

def render_template(app, filename: str, **kwargs) -> HTMLResponse:
    template = _get_template(app, filename)
    rendered_template: str = template.render(**kwargs)
    
    return HTMLResponse(rendered_template)

async def render_template_string_async(app, template_string: str, **kwargs) -> str:
    template: Template = _get_template_string(app, template_string)
    return await template.render_async(**kwargs)

def render_template_string(app, template_string: str, **kwargs) -> str:
    template: Template = _get_template_string(app, template_string)
    return template.render(**kwargs)