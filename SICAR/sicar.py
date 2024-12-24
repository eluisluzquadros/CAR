# /content/CAR/SICAR/sicar.py
"""SICAR Class Module for accessing the CAR system."""

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
import logging

from SICAR.http_client import HttpClient
from SICAR.drivers import Captcha, Tesseract, Paddle
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
    """Class representing the SICAR system."""

    def __init__(self, driver: Captcha = Paddle, debug: bool = False):
        """Initialize SICAR instance."""
        super().__init__()
        self._driver = driver()
        self._client = HttpClient()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._debug = debug

        # Set specific headers for captcha requests
        self._captcha_headers = {
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Sec-Fetch-Dest": "image",
            "Sec-Fetch-Mode": "no-cors",
            "Referer": self._INDEX
        }

    def _download_captcha(self) -> Image:
        """Download and process captcha image."""
        try:
            # First visit the index page to initialize session
            response = self._client.get(self._INDEX)
            
            # Generate random ID for captcha (similar to what the website does)
            captcha_id = str(random.randint(100000, 999999))
            
            # Set specific headers for image download
            headers = {
                'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
                'Referer': self._RELEASE_DATE,
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'same-origin'
            }
            
            # Get captcha URL with ID
            url = self.get_recaptcha_url(captcha_id)
            
            # Download the captcha
            self._logger.debug(f"Downloading captcha from {url}")
            response = self._client.get(url, headers=headers)
            
            try:
                captcha = Image.open(io.BytesIO(response.content))
                # Save for debugging
                if self._debug:
                    os.makedirs('debug', exist_ok=True)
                    captcha.save('debug/captcha.png')
                return captcha
            except Exception as img_error:
                self._logger.error(f"Failed to process image data: {str(img_error)}")
                raise FailedToDownloadCaptchaException() from img_error
                
        except Exception as error:
            self._logger.error(f"Failed to download captcha: {str(error)}")
            raise FailedToDownloadCaptchaException() from error

    def _download_polygon(
        self,
        state: State,
        polygon: Polygon,
        captcha: str,
        folder: str,
    ) -> Path:
        """Download polygon data for state."""
        try:
            params = {
                "idEstado": state.value,
                "tipoBase": polygon.value,
                "ReCaptcha": captcha
            }
            
            query = urlencode(params)
            url = f"{self._DOWNLOAD_BASE}?{query}"
            output_path = Path(os.path.join(folder, f"{state.value}_{polygon.value}")).with_suffix(".zip")
            
            if self._client.download_file(url, output_path):
                return output_path
            raise FailedToDownloadPolygonException()
            
        except Exception as error:
            self._logger.error(f"Failed to download polygon: {str(error)}")
            raise FailedToDownloadPolygonException() from error

    def download_state(
        self,
        state: Union[State, str],
        polygon: Union[Polygon, str],
        folder: Union[Path, str] = Path("temp"),
        tries: int = 25
    ) -> Optional[Path]:
        """Download state data with retry logic."""
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

        info = f"'{polygon.value}' for '{state.value}'"
        
        for attempt in range(tries, 0, -1):
            try:
                captcha_image = self._download_captcha()
                captcha = self._driver.get_captcha(captcha_image)

                if len(captcha) == 5:
                    if self._debug:
                        self._logger.info(f"[{attempt:02d}] - Requesting {info} with captcha '{captcha}'")

                    return self._download_polygon(
                        state=state,
                        polygon=polygon,
                        captcha=captcha,
                        folder=folder,
                    )
                elif self._debug:
                    self._logger.warning(f"[{attempt:02d}] - Invalid captcha '{captcha}' for {info}")
                    
            except (FailedToDownloadCaptchaException, FailedToDownloadPolygonException) as error:
                if self._debug:
                    self._logger.error(f"[{attempt:02d}] - {error} When requesting {info}")
                    
            # Add random delay between attempts
            time.sleep(random.uniform(1, 2))

        return None

    def download_country(
        self,
        polygon: Union[Polygon, str],
        folder: Union[Path, str] = Path("brazil"),
        tries: int = 25
    ) -> Dict:
        """Download data for all states."""
        result = {}
        for state in State:
            state_folder = Path(os.path.join(folder, f"{state}"))
            state_folder.mkdir(parents=True, exist_ok=True)

            result[str(state)] = self.download_state(
                state=state,
                polygon=polygon,
                folder=state_folder,
                tries=tries
            )
        return result

    def get_release_dates(self) -> Dict:
        """Get state data release dates."""
        try:
            response = self._client.get(self._RELEASE_DATE)
            return self._parse_release_dates(response.content)
        except Exception as error:
            raise FailedToGetReleaseDateException() from error

    def _parse_release_dates(self, response: bytes) -> Dict:
        """Parse release dates from HTML response."""
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

                if state in [s.value for s in State] and date:
                    state_dates[State(state)] = date

            return state_dates
        except Exception as e:
            self._logger.error(f"Failed to parse release dates: {str(e)}")
            raise FailedToGetReleaseDateException() from e

    def close(self):
        """Close the client connection."""
        if self._client:
            self._client.close()

    def __del__(self):
        """Cleanup on deletion."""
        self.close()