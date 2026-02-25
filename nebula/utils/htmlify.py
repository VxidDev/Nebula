from werkzeug.wrappers import Response

def htmlify(html: str, status: int = 200) -> Response:
    return Response(
        html,
        status=status,
        mimetype='text/html'
    )
