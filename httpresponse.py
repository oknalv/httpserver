class HttpResponse:
    """ HTTP response class.
    
    Attributes:
        status (str): the full HTTP status, set to "204 No Content" by default.
        status_code (int): the HTTP status code, set to "204" by default.
        http_version (str): the HTTP version, set to "HTTP/1.1" by default.
        headers (dict of str: str): a dict containing the headers.
        body (str): the body.
    """
    __HTTP_STATUS = {
        100: "Continue",
        101: "Switching Protocols",
        200: "OK",
        201: "Created",
        202: "Accepted",
        203: "Non-Authoritative Information",
        204: "No Content",
        205: "Reset Content",
        206: "Partial Content",
        300: "Multiple Choices",
        301: "Moved Permanently",
        302: "Found",
        303: "See Other",
        304: "Not Modified",
        305: "Use Proxy",
        307: "Temporary Redirect",
        400: "Bad Request",
        401: "Unauthorized",
        402: "Payment Required",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        406: "Not Acceptable",
        407: "Proxy Authentication Required",
        408: "Request Timeout",
        409: "Conflict",
        410: "Gone",
        411: "Length Required",
        412: "Precondition Failed",
        413: "Request Entity Too Large",
        414: "Request-URI Too Long",
        415: "Unsupported Media Type",
        416: "Request Range Not Satisfiable",
        417: "Expectation Failed",
        500: "Internal Server Error",
        501: "Not Implemented",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout",
        505: "HTTP Version Not Supported"
    }

    def __init__(self):
        self.headers = dict()
        self.__status = None
        self.__status_code = None
        self.status = 204
        self.http_version = "HTTP/1.1"
        self.__body = None

    @property
    def status_code(self):
        """ int: the HTTP status code.
        """
        return self.__status_code

    @property
    def status(self):
        """ str: the full HTTP status.
        """
        return self.__status

    @status.setter
    def status(self, status_code):
        """ It gets the just the HTTP code and adds the text explanation that follows the code.

        Args:
            status_code (int): the HTTP status code.
        """
        self.__status_code = status_code
        status_str = str(self.__status_code) + " "
        try:
            status_str += self.__HTTP_STATUS[self.__status_code]

            if self.__status_code == 204:
                self.body = None

            self.__status = status_str

        except KeyError:
            self.__status = "501 " + self.__HTTP_STATUS[501]

    @property
    def body(self):
        """ str: the body.
        """
        return self.__body

    @body.setter
    def body(self, value):
        """ Sets the body and if it is not `None`, adds the "Content-Length" header, otherwise it deletes it.
        
        Args:
            value (bytes): the body.
        """
        if value is not None:
            if self.__status_code == 204:
                self.status = 200

            self.__body = value
            self.headers["Content-Length"] = str(len(value))
        else:
            self.__body = None
            if "Content-Length" in self.headers:
                self.headers.pop("Content-Length", None)

    def build(self):
        """ Builds the response string and returns it as `bytes`.

        Returns:
            The full HTTP response as `bytes`.
        """
        response_string = self.http_version + " " + self.status + "\r\n"
        for key in self.headers.keys():
            response_string += str(key) + ": " + self.headers[key] + "\r\n"

        response_string += "\r\n"
        response_bytes = response_string.encode("utf-8")
        if self.body:
            response_bytes += self.body

        return response_bytes
