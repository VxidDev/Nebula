from werkzeug.wrappers import Response
import json

def jsonify(dictionary: dict, status: int = 200) -> Response:
    return Response(
        json.dumps(dictionary),
        status=status,
        mimetype='application/json'
    )
