"""SICAR - Tool designed for students, researchers, data scientists or anyone who would like to have access to SICAR files."""

# SICAR/drivers/__init__.py
from .captcha import Captcha
from .tesseract import Tesseract

__all__ = ['Captcha', 'Tesseract']