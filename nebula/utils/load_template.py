def load_template(app, filename: str) -> str:
    """
    Open and read file from ./templates/<filepath>
    """
    try:
        with open(f"{app.templates_dir}/{filename}", "r") as file:
            content = file.read()
        return content
    except FileNotFoundError:
        raise TemplateNotFound(f"File: '{filename}' not found in {app.templates_dir} directory.")