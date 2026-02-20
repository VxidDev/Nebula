from urllib.parse import urlparse , parse_qs

class Route:
    """
    Represents a single HTTP route in the server.

    Attributes:
        path (str): path that client had requested.
        query_params (str): query parameters identified from path.
    """
    def __init__(self , path: str):
        self.PARSED_PATH = urlparse(path)
        self.path = self.PARSED_PATH.path 
        self.query_params = parse_qs(self.PARSED_PATH.query)
