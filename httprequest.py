class HttpRequest:
    """ HTTP request class.
    
    Attributes:
        method (str): the HTTP method.
        request_uri (str): the request URI.
        query_string (str): the query string.
        http_version (str): the HTTP version.
        headers (dict of str: str): a `dict` containing the headers.
        body (str): the body.
    """
    def __init__(self, client):
        """ The constructor parses the HTTP request.

        Args:
            client (socket.socket): the client socket.

        Raises:
            BadRequestException: If the request cannot be parsed.
        """
        self.method = None
        self.request_uri = None
        self.query_string = None
        self.http_version = None
        self.headers = dict()
        self.body = None
        if client is not None:
            with client.makefile() as request_file:
                try:
                    line = request_file.readline()
                    line_split = line.split(" ")
                    self.method = line_split[0]
                    full_uri = line_split[1].split("?")
                    self.request_uri = full_uri[0]
                    self.query_string = "" if len(full_uri) <= 1 else full_uri[1]
                    self.http_version = line_split[2]
                    line = request_file.readline()
                    while line != "\r\n" and line != "\n":
                        line_split = line.split(": ")
                        self.headers[line_split[0]] = line_split[1].strip()
                        line = request_file.readline()

                    if "Content-Length" in self.headers:
                        self.body = request_file.read(int(self.headers["Content-Length"]))

                except IndexError:
                    raise HttpRequestParseErrorException()


class HttpRequestParseErrorException(Exception):
    """ An exception to raise if the HTTP request is not well formed.
    """
    pass
