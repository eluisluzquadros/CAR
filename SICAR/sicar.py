"""
SICAR Class Module.

This module defines a class representing the Sicar system for managing environmental rural properties in Brazil.
"""

import io
import os
import time
import random
from PIL import Image
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
        self._client = HttpClient(verify_ssl=False)
        self._client.set_headers(headers)
        self._initialize_cookies()

    def get_release_dates(self) -> Dict:
        """Get release date for each state in SICAR system."""
        try:
            response = self._client.get(self._RELEASE_DATE)
            return self._parse_release_dates(response.content)
        except Exception as error:
            raise FailedToGetReleaseDateException() from error

    def _parse_release_dates(self, response: bytes) -> Dict:
        """Parse raw html getting states and release date."""
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

    def _initialize_cookies(self):
        """Initialize cookies by making the initial request."""
        try:
            self._client.get(self._INDEX)
        except Exception:
            pass

    def _download_captcha(self) -> Image:
        """Download a captcha image from the SICAR system."""
        try:
            url = f"{self._RECAPTCHA}?{urlencode({'id': int(random.random() * 1000000)})}"
            
            # Configurar headers específicos para o captcha
            headers = {
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'same-origin',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Tentar download com retry
            for attempt in range(3):
                try:
                    response = self._client.get(url, headers=headers, timeout=30.0)
                    if response.status_code == 200:
                        try:
                            return Image.open(io.BytesIO(response.content))
                        except Exception as img_error:
                            print(f"Erro ao processar imagem: {str(img_error)}")
                            raise
                except Exception as e:
                    print(f"Tentativa {attempt + 1} falhou: {str(e)}")
                    if attempt < 2:  # Se não for a última tentativa
                        time.sleep(2 * (attempt + 1))  # Espera progressiva
                    continue
            
            raise FailedToDownloadCaptchaException()
            
        except Exception as error:
            print(f"Erro ao baixar captcha: {str(error)}")
            raise FailedToDownloadCaptchaException() from error

    def _download_polygon(self, state: State, polygon: Polygon, captcha: str, 
                         folder: str, chunk_size: int = 1024) -> Path:
        """Download polygon for the specified state."""
        query = urlencode({
            "idEstado": state.value,
            "tipoBase": polygon.value,
            "ReCaptcha": captcha
        })
        
        url = f"{self._DOWNLOAD_BASE}?{query}"
        
        try:
            with self._client.stream(url) as response:
                if response.status_code != 200:
                    raise UrlNotOkException(url)

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

    def download_state(self, state: State | str, polygon: Polygon | str, 
                      folder: Path | str = Path("temp"), tries: int = 25,
                      debug: bool = False, chunk_size: int = 1024) -> Path | bool:
        """Download the polygon for the specified state."""
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
                captcha = self._driver.get_captcha(self._download_captcha())

                if len(captcha) == 5:
                    if debug:
                        print(f"[{tries:02d}] - Requesting {info} with captcha '{captcha}'")

                    return self._download_polygon(
                        state=state,
                        polygon=polygon,
                        captcha=captcha,
                        folder=folder,
                        chunk_size=chunk_size,
                    )
                elif debug:
                    print(f"[{tries:02d}] - Invalid captcha '{captcha}' to request {info}")
            except (FailedToDownloadCaptchaException, FailedToDownloadPolygonException) as error:
                if debug:
                    print(f"[{tries:02d}] - {error} When requesting {info}")
            finally:
                tries -= 1
                time.sleep(random.random() + random.random())

        return False

    def download_country(self, polygon: Polygon | str, folder: Path | str = Path("brazil"),
                        tries: int = 25, debug: bool = False, chunk_size: int = 1024):
        """Download polygon for the entire country."""
        result = {}
        for state in State:
            Path(os.path.join(folder, f"{state}")).mkdir(parents=True, exist_ok=True)

            result[str(state)] = self.download_state(
                state=state,
                polygon=polygon,
                folder=folder,
                tries=tries,
                debug=debug,
                chunk_size=chunk_size,
            )
        return result