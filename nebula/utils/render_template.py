from jinja2 import Environment , FileSystemLoader , Template
from nebula.response import HTMLResponse

class TemplateRendererError(BaseException):
    pass

async def render_template(app, filename: str, **kwargs) -> HTMLResponse:
    if not app.jinja_env:
        raise TemplateRendererError("Template renderer not initialized.")

    template: Template = app.jinja_env.get_template(filename)
    rendered_template: str = await template.render_async(**kwargs) # Keep render for now, will change to render_async later

    return HTMLResponse(rendered_template)

async def render_template_string(app, template_string: str, **kwargs) -> str:
    if not app.jinja_env:
        raise TemplateRendererError("Template renderer not initialized.")

    template: Template = app.jinja_env.from_string(template_string)
    return await template.render_async(**kwargs)