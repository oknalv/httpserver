import hashlib
import base64
import re

from httpresponse import HttpResponse
from httprequest import HttpRequest, HttpRequestParseErrorException
from filegetter import FileGetter


class HttpRequestHandler:
    """ Handles an HTTP request.
    """

    __ENDPOINTS = dict()

    __API_URI = "/api"

    __HOOKS = {
        "AFTER_PARSING": [],
        "BEFORE_SENDING": [],
        "AFTER_SENDING": []
    }

    def __init__(self, client, address):
        """ Handles the request and sends a response to the client.

        Args:
            client (socket.socket): The client of the request.
            address (tuple(str, int)): The client address and port, for logging purposes.
        """
        self.__client = client
        self.__address = address
        self.__response = HttpResponse()
        self.__request = None
        self.__close_connection = True
        stop_handling_request = False
        try:
            """ First parses the HTTP request and, if there are hooks to call after parsing them, calls them.
            """
            self.__request = HttpRequest(client)
            self.__after_parsing()

        except StopHandlingRequestException:
            """ If there is any reason to stop the regular execution of the request handling, the after parsing hooks
            have to raise a `StopHandlingRequestException`. See `after_parsing_request` method for more information.
            """
            stop_handling_request = True

        except HttpRequestParseErrorException:
            """ If the request cannot be parsed, it returns a 400 HTTP error code to the client.
            """
            stop_handling_request = True
            self.__response.status = 400

        if not stop_handling_request:
            request_uri = self.__request.request_uri
            request_method = self.__request.method
            """ Checks if the request has a valid HTTP method, if not, it returns a 400 HTTP error code to the client.
            """
            if request_method in ["GET", "POST", "HEAD", "PUT", "DELETE", "TRACE", "OPTIONS", "CONNECT", "PATCH"]:
                """ Checks if the request is for the API or the app and handles it accordingly.
                """
                if request_uri == self.__API_URI or request_uri.startswith(self.__API_URI + "/"):
                    self.__handle_api_request()
                else:
                    self.__handle_app_request()

            else:
                self.__response.status = 400

            self.__end_handling()

        else:
            self.__end_handling()

    def __end_handling(self):
        """ Ends the handling, either closing or leaving the connection open, also prints logging data.
        """
        if self.__request is not None:
            print("{}:{} - {}: {} {}".format(self.__address[0], self.__address[1], self.__request.method,
                                             self.__request.request_uri, self.__response.status))
        else:
            print("{}:{} - {}".format(self.__address[0], self.__address[1], self.__response.status))

        self.__before_sending()
        self.__client.send(self.__response.build())
        self.__after_sending()
        if self.__close_connection:
            self.__client.close()

    def __after_parsing(self):
        """ Just calls the `__hooks_execution` method with the name of the after parsing hook list.
        """
        self.__hooks_execution("AFTER_PARSING")

    def __before_sending(self):
        """ Just calls the `__hooks_execution` method with the name of the before sending hook list.
        """
        self.__hooks_execution("BEFORE_SENDING")

    def __after_sending(self):
        """ Just calls the `__hooks_execution` method with the name of the after sending hook list.
        """
        self.__hooks_execution("AFTER_SENDING")

    def __hooks_execution(self, hook_list_name):
        """ Executes one by one every hook function in the list given by the name in `hook_list_name`. It passes the
        request and the response to the function required by the use of the different hook decorators. The hook
        functions has to have `request` and `response` as arguments.

        Args:
            hook_list_name (str): The name of the hook list.
        """
        # TODO: reference here the explanation of its hook method like: "See that method"
        hook_list = HttpRequestHandler.__HOOKS[hook_list_name]
        for function in hook_list:
            function(self.__request, self.__response)

    def __handle_web_socket_request(self, ws_handler):
        """ Sends the WebSocket handshake and delegates the handling to the class set in `ws_handler`.

        Args:
            ws_handler (WebSocketHandler): the WebSocketHandler class.
        """
        self.__response.status = 101
        self.__response.headers["Upgrade"] = "websocket"
        self.__response.headers["Connection"] = "Upgrade"
        hasher = hashlib.sha1()
        header_hash = self.__request.headers["Sec-WebSocket-Key"] + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        hasher.update(header_hash.encode("utf-8"))
        self.__response.headers["Sec-WebSocket-Accept"] = base64.b64encode(hasher.digest()).decode("utf-8")
        self.__close_connection = False
        self.__end_handling()
        ws_handler(self.__client)

    def __handle_app_request(self):
        """ Handles a file request. If the request is not GET or HEAD, sends a 405 HTTP error code to the client. If the
        file doesn't exist, sends a 404 HTTP error code to the client.
        """
        allowed_methods = ["GET", "HEAD"]
        if self.__request.method not in allowed_methods:
            self.__set_method_not_allowed(allowed_methods)

        else:
            request_uri = self.__request.request_uri[1:]
            try:
                self.__response.body, self.__response.headers["Content-Type"] = FileGetter.get_file(request_uri)

            except IOError:
                self.__response.status = 404

    def __handle_api_request(self):
        """ Handles an API request. It supports static and dynamic API requests. To make a dynamic API endpoint, the
        path of the endpoint has to have at least one dynamic part, and the syntax is just having a ":" before of the
        dynamic part, for example, in "/api/:dyn", ":dyn" is a dynamic part, when making a request its path can be
        something like this; "/api/1234". The endpoint function have to have the same amount of arguments as dynamic
        parts, for example, following the previous example, a function that handles a GET request should be declared
        like "def do_get(dyn)" with the decorator "HttpRequestHandler.get('/api/:dyn'). The name of the arguments
        doesn't have to fit the name of the dynamic parts necessarily, but it is recommended.
        """
        """ Deletes the API URI part of the request URI to use it for searching in the endpoints.
        """
        request_uri = self.__request.request_uri[len(self.__API_URI):]
        request_method = self.__request.method
        """ Checks if the request URI exists non dynamically. If it doesn't exist, tries to match the dynamic endpoints
        with the request URI.
        """
        if request_uri in self.__ENDPOINTS:
            resource = self.__ENDPOINTS[request_uri]
            """ Checks if the request method is correct and finishes. If it is not, it sends a 405 HTTP error code to
            the client.
            """
            if request_method in resource:
                self.__end_api_request(request_method, resource)

            else:
                self.__set_method_not_allowed(resource.keys())

        else:
            success = False
            for uri in self.__ENDPOINTS:
                """ To be a dynamic URI, it has to have at least one ":" character.
                """
                if ":" not in uri:
                    continue

                else:
                    regex = self.__get_regex_from_dynamic_uri(uri)
                    if re.match(regex, request_uri):
                        success = True
                        resource = self.__ENDPOINTS[uri]
                        """ Checks if the request method is correct and finishes. If it is not, it sends a 405 HTTP
                        error code to the client.
                        """
                        if request_method in resource:
                            """ Gets the arguments from the request URI.
                            """
                            arguments = self.__get_arguments_from_dynamic_uri(regex, request_uri)
                            self.__end_api_request(request_method, resource, arguments)

                        else:
                            self.__set_method_not_allowed(resource.keys())

                        break

            if not success:
                """ In case the request doesn't fit any of the API URIs, either static or dynamic, sends a 404 HTTP
                status code to the client.
                """
                self.__response.status = 404

    def __set_method_not_allowed(self, allowed_methods):
        """ Sets the 405 HTTP error code and the allowed methods in the response.

        Args:
            allowed_methods (list of str): the allowed methods.
        """
        self.__response.status = 405
        self.__response.headers["Allow"] = ", ".join(allowed_methods)

    def __end_api_request(self, request_method, resource, arguments=list()):
        """ Ends the API request. Sets the result of the execution of the endpoint function to the body of the response.
        If the function has a WebSocket handler class associated, gives the handling of the client to this class.

        Args:
            request_method (str): the request method.
            resource (dict of str: obj): the function with its optional parameters.
            arguments (list of obj): the arguments given by the dynamic URI.
        """
        function_dict = resource[request_method]
        function = function_dict["function"]
        self.__response.body = function(*arguments)
        ws_handler = function_dict["ws_handler"]
        if ws_handler is not None:
            self.__handle_web_socket_request(ws_handler)

    @staticmethod
    def configure(config):
        """ Configures the handler.

        Args:
            config (dict of str: obj):

        Raises:
            ApiUriWrongSyntaxException: if the API URI has wrong syntax.
        """
        if "api_uri" in config:
            """ Configures the base API URI.
            """
            api_uri = config["api_uri"]
            if api_uri is not None and re.match(r"^/.+$", api_uri):
                HttpRequestHandler.__API_URI = api_uri

            else:
                raise ApiUriWrongSyntaxException(api_uri)

        if "app_folder" in config:
            """ Configures the app folder, where all the app files are.
            """
            FileGetter.set_app_folder(config["app_folder"])

        if "file_mappings" in config:
            """ Configures mappings for the files.
            """
            FileGetter.set_file_mappings(config["file_mappings"])

    @staticmethod
    def __get_regex_from_dynamic_uri(uri):
        """ Generates a regular expression given by a dynamic URI.

        Args:
            uri (str): the dynamic URI.

        Returns:
             A regular expression that matches the dynamic URI and the requests to that URI.
        """
        arguments = []
        uri_split = uri.split(":")[1:]
        if len(uri_split) > 0:
            for split in uri_split:
                if split == "":
                    break

                else:
                    arguments.append(split.split("/")[0])

        new_uri = "\/".join(uri.split("/"))
        for argument in arguments:
            new_uri = new_uri.replace(":" + argument, ".+", 1)

        return r"^" + new_uri + "$"

    @staticmethod
    def __get_arguments_from_dynamic_uri(regex, uri):
        """ Gets the arguments from a dynamic URI using the regular expression for that dynamic URI and a request URI.

        Args:
            regex (str): the regular expression that matches the request URI.
            uri (str): the request URI.

        Returns:
            The list of arguments.
        """
        arguments = []
        regex = "/".join(regex[1:-1].split("\/"))
        regex_split = "??.+??".join(regex.split(".+")).split("??")
        regex_split = [x for x in regex_split if x != ""]
        for i in range(len(regex_split)):
            if regex_split[i] != ".+":
                uri = uri.replace(regex_split[i], "", 1)
                continue

            else:
                if i == len(regex_split) - 1:
                    arguments.append(uri)

                else:
                    position = uri.find(regex_split[i+1])
                    argument = uri[:position]
                    arguments.append(argument)
                    uri = uri.replace(argument, "", 1)

        return arguments

    """ Endpoint decorators
    """

    @staticmethod
    def get(uri, ws_handler=None):
        """ Makes an endpoint with the method GET.

        Args:
            uri (str): the endpoint URI.
            ws_handler (WebSocketHandler): an optional WebSocket handler class, in case the request opens a WebSocket
                connection.
        """
        return HttpRequestHandler.__method("GET", uri, ws_handler)

    @staticmethod
    def post(uri, ws_handler=None):
        """ Makes an endpoint with the method POST.

        Args:
            uri (str): the endpoint URI.
            ws_handler (WebSocketHandler): an optional WebSocket handler class, in case the request opens a WebSocket
                connection.
        """
        return HttpRequestHandler.__method("POST", uri, ws_handler)

    @staticmethod
    def head(uri, ws_handler=None):
        """ Makes an endpoint with the method HEAD.

        Args:
            uri (str): the endpoint URI.
            ws_handler (WebSocketHandler): an optional WebSocket handler class, in case the request opens a WebSocket
                connection.
        """
        return HttpRequestHandler.__method("HEAD", uri, ws_handler)

    @staticmethod
    def put(uri, ws_handler=None):
        """ Makes an endpoint with the method PUT.

        Args:
            uri (str): the endpoint URI.
            ws_handler (WebSocketHandler): an optional WebSocket handler class, in case the request opens a WebSocket
                connection.
        """
        return HttpRequestHandler.__method("PUT", uri, ws_handler)

    @staticmethod
    def delete(uri, ws_handler=None):
        """ Makes an endpoint with the method DELETE.

        Args:
            uri (str): the endpoint URI.
            ws_handler (WebSocketHandler): an optional WebSocket handler class, in case the request opens a WebSocket
                connection.
        """
        return HttpRequestHandler.__method("DELETE", uri, ws_handler)

    @staticmethod
    def trace(uri, ws_handler=None):
        """ Makes an endpoint with the method TRACE.

        Args:
            uri (str): the endpoint URI.
            ws_handler (WebSocketHandler): an optional WebSocket handler class, in case the request opens a WebSocket
                connection.
        """
        return HttpRequestHandler.__method("TRACE", uri, ws_handler)

    @staticmethod
    def options(uri, ws_handler=None):
        """ Makes an endpoint with the method OPTIONS.

        Args:
            uri (str): the endpoint URI.
            ws_handler (WebSocketHandler): an optional WebSocket handler class, in case the request opens a WebSocket
                connection.
        """
        return HttpRequestHandler.__method("OPTIONS", uri, ws_handler)

    @staticmethod
    def connect(uri, ws_handler=None):
        """ Makes an endpoint with the method CONNECT.

        Args:
            uri (str): the endpoint URI.
            ws_handler (WebSocketHandler): an optional WebSocket handler class, in case the request opens a WebSocket
                connection.
        """
        return HttpRequestHandler.__method("CONNECT", uri, ws_handler)

    @staticmethod
    def patch(uri, ws_handler=None):
        """ Makes an endpoint with the method PATCH.

        Args:
            uri (str): the endpoint URI.
            ws_handler (WebSocketHandler): an optional WebSocket handler class, in case the request opens a WebSocket
                connection.
        """
        return HttpRequestHandler.__method("PATCH", uri, ws_handler)

    @staticmethod
    def __method(method, uri, ws_handler):
        """ Makes the actual endpoint.

        Args:
            method (str): the method that has to be used for this URI.
            uri (str): the endpoint URI.
            ws_handler (WebSocketHandler): an optional WebSocket handler class, in case the request opens a WebSocket
                connection.
        Returns:
            The wrapper function.

        Raises:
            ApiRouteWrongSyntaxException: if the URI has wrong syntax.
        """
        if not uri.startswith("/"):
            raise ApiRouteWrongSyntaxException(uri)

        def wrap(f):
            if uri not in HttpRequestHandler.__ENDPOINTS:
                HttpRequestHandler.__ENDPOINTS[uri] = {}

            HttpRequestHandler.__ENDPOINTS[uri][method] = {"function": f, "ws_handler": ws_handler}

        return wrap

    """ Hook decorators
    """

    @staticmethod
    def after_parsing_request(f):
        """ Adds a new hook function to the AFTER_PARSING list. If, for some reason, the execution of the handling has
        to be stopped, for example if the request doesn't have an authentication header, the hook has to raise an
        exception of the type `StopHandlingRequestException`.

        Args:
            f (function): the hook function.
        """
        HttpRequestHandler.__HOOKS["AFTER_PARSING"].append(f)

    @staticmethod
    def before_sending_response(f):
        """ Adds a new hook function to the BEFORE_SENDING list.

        Args:
            f (function): the hook function.
        """
        HttpRequestHandler.__HOOKS["BEFORE_SENDING"].append(f)

    @staticmethod
    def after_sending_response(f):
        """ Adds a new hook function to the AFTER_SENDING list.

        Args:
            f (function): the hook function.
        """
        HttpRequestHandler.__HOOKS["AFTER_SENDING"].append(f)


class ApiRouteWrongSyntaxException(Exception):
    """ Exception to be raised when a API endpoint has wrong syntax.
    """
    def __init__(self, uri):
        message = "API endpoint should start with '/', '{}' was given".format(uri)
        super().__init__(message)


class ApiUriWrongSyntaxException(Exception):
    """ Exception to be raised when the base API URI has wrong syntax.
    """
    def __init__(self, uri):
        message = "API URI should start with '/' and contain at least one character, '{}' was given".format(uri)
        super().__init__(message)


class StopHandlingRequestException(Exception):
    """ Exception to be raised when the request handling has to be stopped after the request parsing.
    """
    pass
