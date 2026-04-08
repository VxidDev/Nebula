from ..response import JSONResponse
import warnings 

def jsonify(dictionary: dict, status: int = 200) -> JSONResponse: # deprecated
    warnings.warn(
        "jsonify utility is deprecated.",
        category=DeprecationWarning,
        stacklevel=2
    )

    return JSONResponse(
        dictionary,
        status_code=status,
    )
