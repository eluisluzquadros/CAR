# Importações necessárias
from contextlib import asynccontextmanager
from .http_client import HttpClient
from .state import State
from .polygon import Polygon
from .url import Url
from .drivers import Captcha, Tesseract

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

class Sicar(Url):
    def __init__(self, driver: Captcha = Tesseract, headers: Dict = None):
        """Initialize Sicar instance with async HTTP client"""
        super().__init__()  # Call parent class constructor first
        self._driver = driver()
        self._client = None
        self._headers = headers
        self._loop = asyncio.get_event_loop()
        self._logger = logging.getLogger(self.__class__.__name__)

    @asynccontextmanager
    async def get_sicar_client(self):
        """Context manager for handling Sicar client lifecycle"""
        try:
            await self._init_client()
            yield self
        finally:
            await self.close()

    async def _init_client(self):
        """Initialize HTTP client if not already initialized"""
        if not self._client:
            self._client = HttpClient(verify_ssl=False)
            await self._client.create_session()
            if self._headers:
                self._client.set_headers(self._headers)
            await self._initialize_cookies()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def download_sicar():
    """Main asynchronous function to handle SICAR downloads"""
    try:
        async with get_sicar_client() as sicar:
            # Obter datas de lançamento
            try:
                release_dates = await sicar.get_release_dates_async()
                logger.info("Release dates: %s", release_dates)
            except Exception as e:
                logger.error("Failed to get release dates: %s", str(e))
                return

            # Fazer download do estado
            try:
                result = await sicar.download_state_async(
                    state=State.AC,
                    polygon=Polygon.AREA_PROPERTY,
                    debug=True  # Enable debug mode to see progress
                )
                logger.info("Download result: %s", result)
            except Exception as e:
                logger.error("Failed to download state data: %s", str(e))
                return

    except Exception as e:
        logger.error("Unexpected error: %s", str(e))

# Entry point with proper error handling
def main():
    """Main entry point with different runtime environments handling"""
    try:
        # If running in Jupyter/Colab
        asyncio.get_event_loop().run_until_complete(download_sicar())
    except RuntimeError:
        # If running in a regular Python environment
        asyncio.run(download_sicar())

if __name__ == "__main__":
    main()