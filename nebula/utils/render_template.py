from jinja2 import Template
from nebula.response import HTMLResponse

class TemplateRendererError(BaseException):
    pass

def _get_template(app, filename: str, is_async_env: bool = True) -> Template:
    jinja_env = app.jinja_env if is_async_env else app.jinja_env_sync
    if not jinja_env:
        raise TemplateRendererError("Template renderer not initialized.")

    template: Template = jinja_env.get_template(filename)
    return template

def _get_template_string(app, template_string: str, is_async_env: bool = True) -> Template:
    jinja_env = app.jinja_env if is_async_env else app.jinja_env_sync
    if not jinja_env:
        raise TemplateRendererError("Template renderer not initialized.")

    template: Template = jinja_env.from_string(template_string)
    return template

async def render_template_async(app, filename: str, **kwargs) -> HTMLResponse:
    template = _get_template(app, filename, is_async_env=True)
    rendered_template: str = await template.render_async(**kwargs)

    return HTMLResponse(rendered_template)

def render_template(app, filename: str, **kwargs) -> HTMLResponse:
    template = _get_template(app, filename, is_async_env=False)
    rendered_template: str = template.render(**kwargs)
    
    return HTMLResponse(rendered_template)

async def render_template_string_async(app, template_string: str, **kwargs) -> str:
    template: Template = _get_template_string(app, template_string, is_async_env=True)
    return await template.render_async(**kwargs)

def render_template_string(app, template_string: str, **kwargs) -> str:
    template: Template = _get_template_string(app, template_string, is_async_env=False)
    return template.render(**kwargs)