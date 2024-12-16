"""Drivers for SICAR captcha recognition."""

from SICAR.drivers.captcha import Captcha
from SICAR.drivers.tesseract import Tesseract

# Lazy loading do Paddle para evitar erro de importação se não estiver disponível
def get_paddle():
    try:
        from SICAR.drivers.paddle import Paddle
        return Paddle
    except ImportError:
        return None

Paddle = get_paddle()