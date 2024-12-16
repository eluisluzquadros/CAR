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

    def download_state(
        self,
        state: State | str,
        polygon: Polygon | str,
        folder: Path | str = Path("temp"),
        tries: int = 25,
        debug: bool = False,
        chunk_size: int = 1024,
    ) -> Path | bool:
        """
        Download the polygon or other output format for the specified state.

        Parameters:
            state (State | str): The state for which to download the files. It can be either a `State` enum value or a string representing the state's abbreviation.
            polygon (Polygon | str): The polygon to download the files. It can be either a `Polygon` enum value or a string representing the polygon's.
            folder (Path | str, optional): The folder path where the downloaded data will be saved. Defaults to "temp".
            tries (int, optional): The number of attempts to download the data. Defaults to 25.
            debug (bool, optional): Whether to print debug information. Defaults to False.
            chunk_size (int, optional): The size of each chunk to download. Defaults to 1024.

        Returns:
            Path | bool: The path to the downloaded data if successful, or False if download fails.

        Note:
            This method attempts to download the polygon for the specified state.
            It tries multiple times, using a captcha for verification. The downloaded data is saved to the specified folder.
            The method returns the path to the downloaded data if successful, or False if the download fails after the specified number of tries.
        """
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
                        print(
                            f"[{tries:02d}] - Requesting {info} with captcha '{captcha}'"
                        )

                    return self._download_polygon(
                        state=state,
                        polygon=polygon,
                        captcha=captcha,
                        folder=folder,
                        chunk_size=chunk_size,
                    )
                elif debug:
                    print(
                        f"[{tries:02d}] - Invalid captcha '{captcha}' to request {info}"
                    )
            except (
                FailedToDownloadCaptchaException,
                FailedToDownloadPolygonException,
            ) as error:
                if debug:
                    print(f"[{tries:02d}] - {error} When requesting {info}")
            finally:
                tries -= 1
                time.sleep(random.random() + random.random())

        return False

    def download_country(
        self,
        polygon: Polygon | str,
        folder: Path | str = Path("brazil"),
        tries: int = 25,
        debug: bool = False,
        chunk_size: int = 1024,
    ):
        """
        Download polygon for the entire country.

        Parameters:
            polygon (Polygon | str): The polygon to download the files. It can be either a `Polygon` enum value or a string representing the polygon's.
            folder (Path | str, optional): The folder path where the downloaded files will be saved. Defaults to 'brazil'.
            tries (int, optional): The number of download attempts allowed per state. Defaults to 25.
            debug (bool, optional): Whether to enable debug mode with additional print statements. Defaults to False.
            chunk_size (int, optional): The size of each chunk to download. Defaults to 1024.

        Returns:
            Dict: A dictionary containing the results of the download operation.
                The keys are the state abbreviations, and the values are dictionaries representing the results of downloading each state.
                Each state's dictionary follows the same structure as the result of the `download_state` method.
                If a download fails for a state the corresponding value will be False.
        """
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

    def get_release_dates(self) -> Dict:
        """
        Get release date for each state in SICAR system.

        Returns:
            Dict: A dict containing state sign as keys and release date as string in dd/mm/yyyy format.

        Raises:
            FailedToGetReleaseDateException: If the page with release date fails to load.
        """
        try:
            response = self._get(f"{self._RELEASE_DATE}")
            return self._parse_release_dates(response.content)
        except UrlNotOkException as error:
            raise FailedToGetReleaseDateException() from error
