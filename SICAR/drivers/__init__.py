# SICAR/drivers/__init__.py
"""Drivers for SICAR captcha recognition with improved error handling."""

import logging
from SICAR.drivers.captcha import Captcha, CaptchaProcessingError
from SICAR.drivers.tesseract import Tesseract

logger = logging.getLogger(__name__)

# Lazy loading of Paddle to avoid import errors
def get_paddle():
    try:
        from SICAR.drivers.paddle import Paddle
        logger.debug("Successfully imported Paddle OCR driver")
        return Paddle
    except ImportError as e:
        logger.warning(f"Paddle OCR not available: {str(e)}")
        return None

Paddle = get_paddle()

__all__ = ['Captcha', 'Tesseract', 'Paddle', 'CaptchaProcessingError']