# /content/CAR/SICAR/__init__.py
"""SICAR - Tool designed for students, researchers, data scientists or anyone who would like to have access to SICAR files."""

from .state import State
from .polygon import Polygon
from .url import Url
from .exceptions import (
    SICARException,
    UrlNotOkException,
    PolygonNotValidException,
    StateCodeNotValidException,
    FailedToDownloadCaptchaException,
    FailedToDownloadPolygonException,
    FailedToGetReleaseDateException,
    ConnectionTimeoutException,
    SSLVerificationException,
    SessionClosedException
)
from .drivers.captcha import Captcha, CaptchaProcessingError
from .drivers.tesseract import Tesseract
from .drivers.paddle import Paddle
from .sicar import Sicar

__version__ = '0.0.2'

__all__ = [
    'Sicar',
    'State',
    'Polygon',
    'Url',
    'Captcha',
    'Tesseract',
    'Paddle',
    'CaptchaProcessingError',
    'SICARException',
    'UrlNotOkException',
    'PolygonNotValidException',
    'StateCodeNotValidException',
    'FailedToDownloadCaptchaException',
    'FailedToDownloadPolygonException',
    'FailedToGetReleaseDateException',
    'ConnectionTimeoutException',
    'SSLVerificationException',
    'SessionClosedException'
]
