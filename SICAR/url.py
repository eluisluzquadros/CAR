# SICAR/url.py
"""
URL Class Module.

This module defines a class representing CAR URLs for various resources.
"""
from typing import ClassVar

class Url:
    """Class representing CAR URLs for various resources."""

    # Base URLs
    _BASE: ClassVar[str] = "https://consultapublica.car.gov.br/publico"
    _INDEX: ClassVar[str] = f"{_BASE}/imoveis/index"
    _DOWNLOAD_BASE: ClassVar[str] = f"{_BASE}/estados/downloadBase"
    _RELEASE_DATE: ClassVar[str] = f"{_BASE}/estados/downloads"
    _RECAPTCHA_BASE: ClassVar[str] = f"{_BASE}/municipios/ReCaptcha"
    

    @classmethod
    def get_base_url(cls) -> str:
        """Get the base URL for the CAR system."""
        return cls._BASE

    @classmethod
    def get_index_url(cls) -> str:
        """Get the URL for the main index page."""
        return cls._INDEX

    @classmethod
    def get_download_base_url(cls) -> str:
        """Get the URL for downloading base data."""
        return cls._DOWNLOAD_BASE

    @classmethod
    def get_recaptcha_url(cls, captcha_id: str) -> str:
        """Get URL for captcha with specific ID."""
        return f"{cls._RECAPTCHA_BASE}?id={captcha_id}"

    @classmethod
    def get_release_date_url(cls) -> str:
        """Get the URL for release dates."""
        return cls._RELEASE_DATE