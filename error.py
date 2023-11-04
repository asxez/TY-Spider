from requests import RequestException


class Error(Exception):
    def __init__(self, message):
        super().__init__(message)


class IIndexError(Error):
    """即IndexError，避免名称重复"""
    pass


class RequestError(RequestException):
    def __init__(self, message):
        super().__init__(message)