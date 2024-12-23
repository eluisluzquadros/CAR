"""
SICAR Class Module.

This module defines a class representing the Sicar system for managing environmental 
rural properties in Brazil.
"""

import io
import os
import time
import random
from PIL import Image, UnidentifiedImageError
from bs4 import BeautifulSoup
from tqdm import tqdm
from typing import Dict, Union, Optional
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
    """Class representing the Sicar system."""

    def __init__(self, driver: Captcha = Tesseract, headers: Optional[Dict] = None):
        """Initialize Sicar instance."""
        super().__init__()
        self._driver = driver()
        self._client = HttpClient()
        if headers:
            self._client.set_headers(headers)

    def _download_captcha(self) -> Image:
        """Download captcha image."""
        try:
            url = f"{self._RECAPTCHA}?{urlencode({'id': int(random.random() * 1000000)})}"
            
            response = self._client.get(url)
            
            try:
                captcha = Image.open(io.BytesIO(response.content))
                if captcha.mode != 'RGB':
                    captcha = captcha.convert('RGB')
                return captcha
            except UnidentifiedImageError as img_error:
                raise FailedToDownloadCaptchaException() from img_error
                
        except Exception as error:
            raise FailedToDownloadCaptchaException() from error

    def _download_polygon(
        self,
        state: State,
        polygon: Polygon,
        captcha: str,
        folder: str,
    ) -> Path:
        """Download polygon data."""
        params = {
            "idEstado": state.value,
            "tipoBase": polygon.value,
            "ReCaptcha": captcha
        }
            
        query = urlencode(params)
        url = f"{self._DOWNLOAD_BASE}?{query}"
        output_path = Path(os.path.join(folder, f"{state.value}_{polygon.value}")).with_suffix(".zip")
        
        if self._client.stream_download(url, output_path):
            return output_path
        raise FailedToDownloadPolygonException()

    def download_state(
        self,
        state: State | str,
        polygon: Polygon | str,
        folder: Path | str = Path("temp"),
        tries: int = 25,
        debug: bool = False,
    ) -> Path | bool:
        """Download state data."""
        if isinstance(state, str):
            try:
                state = State(state.upper())
            except ValueError as error:
                raise StateCodeNotValidException(state) from error

        if isinstance(polygon, str):
            try:
                polygon = Polygon(polygon.upper())
            except ValueError as error:
                raise PolygonNotValidException(polygon) from error

        Path(folder).mkdir(parents=True, exist_ok=True)

        captcha = ""
        info = f"'{polygon.value}' for '{state.value}'"

        while tries > 0:
            try:
                captcha_image = self._download_captcha()
                captcha = self._driver.get_captcha(captcha_image)

                if len(captcha) == 5:
                    if debug:
                        print(f"[{tries:02d}] - Requesting {info} with captcha '{captcha}'")

                    return self._download_polygon(
                        state=state,
                        polygon=polygon,
                        captcha=captcha,
                        folder=folder,
                    )
                elif debug:
                    print(f"[{tries:02d}] - Invalid captcha '{captcha}' to request {info}")
                    
            except (FailedToDownloadCaptchaException, FailedToDownloadPolygonException) as error:
                if debug:
                    print(f"[{tries:02d}] - {error} When requesting {info}")
            finally:
                tries -= 1
                time.sleep(random.uniform(1, 2))

        return False

    def download_country(
        self,
        polygon: Polygon | str,
        folder: Path | str = Path("brazil"),
        tries: int = 25,
        debug: bool = False,
    ) -> Dict:
        """Download country-wide data."""
        result = {}
        for state in State:
            state_folder = Path(os.path.join(folder, f"{state}"))
            state_folder.mkdir(parents=True, exist_ok=True)

            result[str(state)] = self.download_state(
                state=state,
                polygon=polygon,
                folder=state_folder,
                tries=tries,
                debug=debug,
            )
        return result

    def get_release_dates(self) -> Dict:
        """Get release dates."""
        try:
            response = self._client.get(self._RELEASE_DATE)
            return self._parse_release_dates(response.content)
        except Exception as error:
            raise FailedToGetReleaseDateException() from error

    def _parse_release_dates(self, response: bytes) -> Dict:
        """Parse release dates from response."""
        try:
            html_content = response.decode("utf-8")
            soup = BeautifulSoup(html_content, "html.parser")
            state_dates = {}

            for state_block in soup.find_all("div", class_="listagem-estados"):
                button_tag = state_block.find(
                    "button", class_="btn-abrir-modal-download-base-poligono"
                )
                state = button_tag.get("data-estado") if button_tag else None

                date_tag = state_block.find("div", class_="data-disponibilizacao")
                date = date_tag.get_text(strip=True) if date_tag else None

                if state in iter(State) and date:
                    state_dates[State(state)] = date

            return state_dates
        except Exception as e:
            raise FailedToGetReleaseDateException() from e

    def close(self):
        """Close the client."""
        if self._client:
            self._client.close()
            self._client = None

    def __del__(self):
        """Cleanup on deletion."""
        self.close()