"""
SICAR Class Module.

This module defines a class representing the Sicar system for managing environmental 
rural properties in Brazil.
"""

import io
import os
import time
import random
import asyncio
import logging
from PIL import Image, UnidentifiedImageError
from bs4 import BeautifulSoup
from tqdm import tqdm
from typing import Dict, Union, Optional
from pathlib import Path
from urllib.parse import urlencode
from contextlib import asynccontextmanager

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
    """Class representing the Sicar system for managing environmental rural properties in Brazil."""

    def __init__(self, driver: Captcha = Tesseract, headers: Optional[Dict] = None):
        """Initialize Sicar instance."""
        super().__init__()
        self._driver = driver()
        self._client = None
        self._headers = headers
        self._logger = logging.getLogger(self.__class__.__name__)

    async def _init_client(self):
        """Initialize HTTP client with retry logic."""
        try:
            if not self._client:
                self._client = HttpClient(verify_ssl=False)
                await self._client.create_session()
                if self._headers:
                    self._client.set_headers(self._headers)
                await self._initialize_cookies()
        except Exception as e:
            self._logger.error(f"Failed to initialize client: {str(e)}")
            raise

    async def _initialize_cookies(self):
        """Initialize session cookies and get initial page."""
        try:
            await self._client.get(self._INDEX)
            self._logger.debug("Cookies initialized successfully")
        except Exception as e:
            self._logger.error(f"Cookie initialization failed: {str(e)}")
            raise

    @asynccontextmanager
    async def get_sicar_client(self):
        """Context manager for handling Sicar client lifecycle."""
        try:
            await self._init_client()
            yield self
        finally:
            if self._client:
                await self.close()

    async def _get_download_token(self, state: State) -> Optional[str]:
        """Get download token for state by parsing the downloads page."""
        try:
            response = await self._client.get(self._RELEASE_DATE)
            content = await response.aread()
            soup = BeautifulSoup(content.decode('utf-8'), 'html.parser')
            
            # Find the button for the specific state
            button = soup.find('button', {
                'class': 'btn-abrir-modal-download-base-poligono',
                'data-estado': state.value
            })
            
            if button:
                return button.get('data-token')  # Modify based on actual token attribute
            return None
            
        except Exception as e:
            self._logger.error(f"Failed to get download token: {str(e)}")
            return None

    async def _download_captcha(self) -> Image:
        """Download captcha with browser-like behavior."""
        try:
            # Add random parameter to avoid caching
            url = f"{self._RECAPTCHA}?{urlencode({'id': int(random.random() * 1000000)})}"
            
            response = await self._client.get(url, is_image=True)
            content = await response.aread()
            
            try:
                captcha = Image.open(io.BytesIO(content))
                if captcha.mode != 'RGB':
                    captcha = captcha.convert('RGB')
                return captcha
            except UnidentifiedImageError as img_error:
                self._logger.error(f"Failed to process captcha image: {str(img_error)}")
                raise FailedToDownloadCaptchaException() from img_error
                
        except Exception as error:
            self._logger.error(f"Failed to download captcha: {str(error)}")
            raise FailedToDownloadCaptchaException() from error

    async def _download_polygon(
        self,
        state: State,
        polygon: Polygon,
        captcha: str,
        folder: str,
        chunk_size: int = 1024,
    ) -> Path:
        """Download polygon data with proper error handling."""
        try:
            # Get download token if needed
            token = await self._get_download_token(state)
            
            # Build query parameters
            params = {
                "idEstado": state.value,
                "tipoBase": polygon.value,
                "ReCaptcha": captcha
            }
            if token:
                params["token"] = token
                
            query = urlencode(params)
            url = f"{self._DOWNLOAD_BASE}?{query}"
            
            async with await self._client.stream(url) as response:
                if response.status_code != 200:
                    raise UrlNotOkException(url)

                content_length = int(response.headers.get("Content-Length", 0))
                content_type = response.headers.get("Content-Type", "")

                if content_length == 0 or not content_type.startswith("application/"):
                    raise FailedToDownloadPolygonException()

                path = Path(os.path.join(folder, f"{state.value}_{polygon.value}")).with_suffix(".zip")
                
                with open(path, "wb") as fd, tqdm(
                    total=content_length,
                    unit="iB",
                    unit_scale=True,
                    desc=f"Downloading polygon '{polygon.value}' for state '{state.value}'"
                ) as progress_bar:
                    async for chunk in response.aiter_bytes(chunk_size):
                        if chunk:
                            fd.write(chunk)
                            progress_bar.update(len(chunk))
                
                return path
                
        except Exception as error:
            self._logger.error(f"Failed to download polygon: {str(error)}")
            raise FailedToDownloadPolygonException() from error

    async def download_state_async(
        self,
        state: State | str,
        polygon: Polygon | str,
        folder: Path | str = Path("temp"),
        tries: int = 25,
        debug: bool = False,
        chunk_size: int = 1024,
    ) -> Path | bool:
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

        captcha = ""
        info = f"'{polygon.value}' for '{state.value}'"

        while tries > 0:
            try:
                captcha_image = await self._download_captcha()
                captcha = self._driver.get_captcha(captcha_image)

                if len(captcha) == 5:
                    if debug:
                        self._logger.info(f"[{tries:02d}] - Requesting {info} with captcha '{captcha}'")

                    return await self._download_polygon(
                        state=state,
                        polygon=polygon,
                        captcha=captcha,
                        folder=folder,
                        chunk_size=chunk_size
                    )
                elif debug:
                    self._logger.warning(f"[{tries:02d}] - Invalid captcha '{captcha}' for {info}")
                    
            except (FailedToDownloadCaptchaException, FailedToDownloadPolygonException) as error:
                if debug:
                    self._logger.error(f"[{tries:02d}] - {error} When requesting {info}")
            finally:
                tries -= 1
                # Exponential backoff with jitter
                await asyncio.sleep(random.uniform(1, 2) * (2 ** (25 - tries)))

        return False

    async def download_country_async(
        self,
        polygon: Polygon | str,
        folder: Path | str = Path("brazil"),
        tries: int = 25,
        debug: bool = False,
        chunk_size: int = 1024,
    ) -> Dict:
        """Download country-wide data with proper error handling."""
        result = {}
        for state in State:
            state_folder = Path(os.path.join(folder, f"{state}"))
            state_folder.mkdir(parents=True, exist_ok=True)

            result[str(state)] = await self.download_state_async(
                state=state,
                polygon=polygon,
                folder=state_folder,
                tries=tries,
                debug=debug,
                chunk_size=chunk_size
            )
        return result

    async def get_release_dates_async(self) -> Dict:
        """Get release dates for all states."""
        try:
            if not self._client:
                await self._init_client()
                
            response = await self._client.get(self._RELEASE_DATE)
            content = await response.aread()
            return self._parse_release_dates(content)
            
        except Exception as error:
            self._logger.error(f"Failed to get release dates: {str(error)}")
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

                if state in iter(State) and date:
                    state_dates[State(state)] = date

            return state_dates
            
        except Exception as e:
            self._logger.error(f"Failed to parse release dates: {str(e)}")
            raise

    async def close(self):
        """Close the HTTP client safely."""
        if self._client:
            await self._client.close()
            self._client = None

    def __del__(self):
        """Cleanup on deletion."""
        try:
            if self._client:
                asyncio.run(self.close())
        except Exception:
            pass