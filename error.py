from requests import RequestException


class Error(Exception):
    def __init__(self, message):
        super().__init__(message)

class RequestError(RequestException):
    def __init__(self, message):
        super().__init__(message)
