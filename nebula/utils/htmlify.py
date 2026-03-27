from ..response import HTMLResponse
import warnings 

def htmlify(html: str, status: int = 200) -> HTMLResponse:
    warnings.warn(
        f"htmlify utility is deprecated.",
        category=DeprecationWarning,
        stacklevel=2
    )

    return HTMLResponse(
        html,
        status_code=status,
    )
