"""
Custom Exception Classes Module.

This module provides custom exception classes for specific error conditions.
"""

class SICARException(Exception):
    """Base exception class for all SICAR exceptions."""
    pass

class UrlNotOkException(SICARException):
    """Exception raised when a URL is inaccessible or returns an error."""
    def __init__(self, url: str):
        self.url = url
        super().__init__(f"Oh no! Failed to access {self.url}!")

class StateCodeNotValidException(SICARException):
    """Exception raised when an invalid state code is encountered."""
    def __init__(self, state: str):
        self.state = state
        super().__init__(f"State code {self.state} not valid!")

class PolygonNotValidException(SICARException):
    """Exception raised when an invalid polygon is encountered."""
    def __init__(self, polygon: str):
        self.polygon = polygon
        super().__init__(f"Polygon {self.polygon} not valid!")

class FailedToDownloadCaptchaException(SICARException):
    """Exception raised when downloading a captcha fails."""
    def __init__(self, message: str = "Failed to download captcha!"):
        super().__init__(message)

class FailedToDownloadPolygonException(SICARException):
    """Exception raised when downloading a polygon fails."""
    def __init__(self, message: str = "Failed to download polygon!"):
        super().__init__(message)

class FailedToGetReleaseDateException(SICARException):
    """Exception raised when get release date fails."""
    def __init__(self, message: str = "Failed to get release date!"):
        super().__init__(message)

class ConnectionTimeoutException(SICARException):
    """Exception raised when a connection times out."""
    def __init__(self, url: str):
        super().__init__(f"Connection timeout while accessing {url}")

class SSLVerificationException(SICARException):
    """Exception raised when SSL verification fails."""
    def __init__(self, url: str):
        super().__init__(f"SSL verification failed for {url}")

class SessionClosedException(SICARException):
    """Exception raised when trying to use a closed session."""
    def __init__(self):
        super().__init__("Attempted to use a closed session")