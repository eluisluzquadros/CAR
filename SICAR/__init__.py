"""SICAR - Tool designed for students, researchers, data scientists or anyone who would like to have access to SICAR files."""

from .sicar import Sicar
from .state import State
from .polygon import Polygon
from .exceptions import (
    UrlNotOkException,
    StateCodeNotValidException,
    PolygonNotValidException,
    FailedToDownloadCaptchaException,
    FailedToDownloadPolygonException,
    FailedToGetReleaseDateException
)

__version__ = '0.0.1'

__all__ = [
    'Sicar',
    'State',
    'Polygon',
    'UrlNotOkException',
    'StateCodeNotValidException',
    'PolygonNotValidException',
    'FailedToDownloadCaptchaException',
    'FailedToDownloadPolygonException',
    'FailedToGetReleaseDateException'
]