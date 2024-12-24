# /content/CAR/SICAR/__init__.py
"""SICAR - Tool designed for students, researchers, data scientists or anyone who would like to have access to SICAR files."""

from .state import State
from .polygon import Polygon
from .url import Url
from .exceptions import (
    UrlNotOkException,
    PolygonNotValidException,
    StateCodeNotValidException,
    FailedToDownloadCaptchaException,
    FailedToDownloadPolygonException,
    FailedToGetReleaseDateException
)
from .drivers.captcha import Captcha, CaptchaProcessingError
from .drivers.tesseract import Tesseract
from .sicar import Sicar

__version__ = '0.0.1'

__all__ = [
    'Sicar',
    'State',
    'Polygon',
    'Url',
    'Captcha',
    'Tesseract',
    'CaptchaProcessingError',
    'UrlNotOkException',
    'PolygonNotValidException',
    'StateCodeNotValidException',
    'FailedToDownloadCaptchaException',
    'FailedToDownloadPolygonException',
    'FailedToGetReleaseDateException'
]