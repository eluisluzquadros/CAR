# /content/CAR/SICAR/drivers/__init__.py
"""
SICAR drivers for captcha processing.

This package contains modules for different OCR engines 
that can be used to solve captchas.
"""

from .captcha import Captcha, CaptchaProcessingError
from .tesseract import Tesseract
from .paddle import Paddle

__all__ = ['Captcha', 'CaptchaProcessingError', 'Tesseract', 'Paddle']