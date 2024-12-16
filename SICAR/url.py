"""
URL Class Module.

This module defines a class representing CAR URLs for various resources.

Classes:
    Url: Class representing CAR URLs for various resources.
"""

class Url:
    """Class representing CAR URLs for various resources."""

    _BASE = "https://consultapublica.car.gov.br/publico"
    _INDEX = f"{_BASE}/imoveis/index"
    _DOWNLOAD_BASE = f"{_BASE}/estados/downloadBase"
    _RECAPTCHA = f"{_BASE}/municipios/ReCaptcha"
    _RELEASE_DATE = f"{_BASE}/estados/downloads"