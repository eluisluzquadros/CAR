"""
SICAR Class Module.

This module defines a class representing the Sicar system for managing environmental rural properties in Brazil.
"""

import io
import os
import time
import random
import asyncio
import logging
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
       """Initialize Sicar instance with async HTTP client"""
       self._driver = driver()
       self._client = None
       self._headers = headers
       self._loop = asyncio.get_event_loop()
       self._logger = logging.getLogger(self.__class__.__name__)

   async def _init_client(self):
       """Initialize HTTP client if not already initialized"""
       if not self._client:
           self._client = HttpClient(verify_ssl=False)
           await self._client.create_session()
           if self._headers:
               self._client.set_headers(self._headers)
           await self._initialize_cookies()

   async def _initialize_cookies(self):
       """Initialize session cookies"""
       try:
           await self._client.get(self._INDEX)
       except Exception as e:
           self._logger.warning(f"Cookie initialization failed: {str(e)}")

   async def _download_captcha(self) -> Image:
       """Download captcha image asynchronously"""
       try:
           url = f"{self._RECAPTCHA}?{urlencode({'id': int(random.random() * 1000000)})}"
           headers = {
               'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
               'Sec-Fetch-Dest': 'image',
               'Sec-Fetch-Mode': 'no-cors',
               'Sec-Fetch-Site': 'same-origin'
           }

           response = await self._client.get(url, headers=headers)
           content = await response.read()
           return Image.open(io.BytesIO(content))

       except Exception as error:
           self._logger.error(f"Failed to download captcha: {str(error)}")
           raise FailedToDownloadCaptchaException() from error

   async def _download_polygon(
       self,
       state: State,
       polygon: Polygon,
       captcha: str,
       folder: str,
       chunk_size: int = 1024
   ) -> Path:
       """Download polygon data asynchronously"""
       query = urlencode({
           "idEstado": state.value,
           "tipoBase": polygon.value,
           "ReCaptcha": captcha
       })
       
       url = f"{self._DOWNLOAD_BASE}?{query}"
       
       try:
           async with await self._client.stream(url) as response:
               if response.status != 200:
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
                   async for chunk in response.content.iter_chunked(chunk_size):
                       if chunk:
                           fd.write(chunk)
                           progress_bar.update(len(chunk))
               
               return path
               
       except Exception as error:
           self._logger.error(f"Failed to download polygon: {str(error)}")
           raise FailedToDownloadPolygonException() from error

   async def get_release_dates_async(self) -> Dict:
       """Get release dates asynchronously"""
       await self._init_client()
       try:
           response = await self._client.get(self._RELEASE_DATE)
           content = await response.read()
           return self._parse_release_dates(content)
       except Exception as error:
           raise FailedToGetReleaseDateException() from error

   def _parse_release_dates(self, response: bytes) -> Dict:
       """Parse release dates from response"""
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
           raise FailedToGetReleaseDateException() from e

   async def download_state_async(
       self,
       state: State | str,
       polygon: Polygon | str,
       folder: Path | str = Path("temp"),
       tries: int = 25,
       debug: bool = False,
       chunk_size: int = 1024
   ) -> Path | bool:
       """Download state data asynchronously"""
       await self._init_client()

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
                       print(f"[{tries:02d}] - Requesting {info} with captcha '{captcha}'")

                   return await self._download_polygon(
                       state=state,
                       polygon=polygon,
                       captcha=captcha,
                       folder=folder,
                       chunk_size=chunk_size
                   )
               elif debug:
                   print(f"[{tries:02d}] - Invalid captcha '{captcha}' to request {info}")
           except (FailedToDownloadCaptchaException, FailedToDownloadPolygonException) as error:
               if debug:
                   print(f"[{tries:02d}] - {error} When requesting {info}")
           finally:
               tries -= 1
               await asyncio.sleep(random.random() + random.random())

       return False

   async def download_country_async(
       self,
       polygon: Polygon | str,
       folder: Path | str = Path("brazil"),
       tries: int = 25,
       debug: bool = False,
       chunk_size: int = 1024
   ) -> Dict:
       """Download country data asynchronously"""
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

   # Synchronous wrapper methods
   def get_release_dates(self) -> Dict:
       """Synchronous wrapper for get_release_dates_async"""
       return asyncio.run(self.get_release_dates_async())

   def download_state(self, *args, **kwargs) -> Path | bool:
       """Synchronous wrapper for download_state_async"""
       return asyncio.run(self.download_state_async(*args, **kwargs))

   def download_country(self, *args, **kwargs) -> Dict:
       """Synchronous wrapper for download_country_async"""
       return asyncio.run(self.download_country_async(*args, **kwargs))

   async def close(self):
       """Close the HTTP client"""
       if self._client:
           await self._client.close()

   def __del__(self):
       """Cleanup on deletion"""
       try:
           if self._client:
               asyncio.run(self.close())
       except Exception:
           pass