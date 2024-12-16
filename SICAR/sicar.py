"""
SICAR Class Module - Refactored version.
"""

import io
import os
import time
import random
from PIL import Image, UnidentifiedImageError
from bs4 import BeautifulSoup
from tqdm import tqdm
from typing import Dict
from pathlib import Path
from urllib.parse import urlencode

from SICAR.http_client import HttpClient
from SICAR.drivers import Captcha, Tesseract
from SICAR.state import State
from SICAR.url import Url
from SICAR.polygon import Polygon
from SICAR.exceptions import (
    UrlNotOkException,
    PolygonNotValidException,
    StateCodeNotValidException,
    FailedToDownloadCaptchaException,
    FailedToDownloadPolygonException,
    FailedToGetReleaseDateException,
)

class Sicar(Url):
    def __init__(self, driver: Captcha = Tesseract, headers: Dict = None):
        self._driver = driver()
        self._client = HttpClient(verify_ssl=False)  # Começamos com SSL desabilitado para o Colab
        self._client.set_headers(headers)
        self._initialize_cookies()

    def _initialize_cookies(self):
        try:
            self._client.get(self._INDEX)
        except Exception:
            pass  # Ignoramos erros na inicialização de cookies
    
    def _download_captcha(self) -> Image:
        url = f"{self._RECAPTCHA}?{urlencode({'id': int(random.random() * 1000000)})}"
        try:
            response = self._client.get(url)
            return Image.open(io.BytesIO(response.content))
        except Exception as error:
            raise FailedToDownloadCaptchaException() from error

    def _download_polygon(
        self,
        state: State,
        polygon: Polygon,
        captcha: str,
        folder: str,
        chunk_size: int = 1024,
    ) -> Path:
        query = urlencode({
            "idEstado": state.value,
            "tipoBase": polygon.value,
            "ReCaptcha": captcha
        })
        
        try:
            with self._client.stream(f"{self._DOWNLOAD_BASE}?{query}") as response:
                response.raise_for_status()
                
                content_length = int(response.headers.get("Content-Length", 0))
                content_type = response.headers.get("Content-Type", "")
                
                if content_length == 0 or not content_type.startswith("application/zip"):
                    raise FailedToDownloadPolygonException()
                
                path = Path(os.path.join(folder, f"{state.value}_{polygon.value}")).with_suffix(".zip")
                
                with open(path, "wb") as fd, tqdm(
                    total=content_length,
                    unit="iB",
                    unit_scale=True,
                    desc=f"Downloading polygon '{polygon.value}' for state '{state.value}'"
                ) as progress_bar:
                    for chunk in response.iter_bytes(chunk_size=chunk_size):
                        if chunk:
                            fd.write(chunk)
                            progress_bar.update(len(chunk))
                
                return path
                
        except Exception as error:
            raise FailedToDownloadPolygonException() from error

    # O resto dos métodos permanece igual