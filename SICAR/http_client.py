# SICAR/http_client.py
"""Async HTTP Client that simulates browser behavior for SICAR website."""

import httpx
import asyncio
from typing import Optional, Dict, Union
import logging
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class HttpClient:
    """Browser-like HTTP client for SICAR website"""
    
    def __init__(self, verify_ssl: bool = False, timeout: float = 30.0):
        self._session: Optional[httpx.AsyncClient] = None
        self._headers = self._get_default_headers()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._verify = verify_ssl
        self._timeout = timeout

    def _get_default_headers(self) -> Dict[str, str]:
        """Get browser-like headers."""
        return {
            "Host": "consultapublica.car.gov.br",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache"
        }

    async def create_session(self):
        """Create browser-like session."""
        try:
            if self._session:
                await self._session.aclose()

            transport = httpx.AsyncHTTPTransport(
                verify=False,
                retries=1  # Reduced retries as we'll handle them manually
            )
            
            self._session = httpx.AsyncClient(
                transport=transport,
                timeout=self._timeout,
                headers=self._headers,
                follow_redirects=True,
                http2=False
            )
            
            self._logger.debug("Created new session")
        except Exception as e:
            self._logger.error(f"Session creation failed: {str(e)}")
            raise

    def _get_image_headers(self) -> Dict[str, str]:
        """Get headers specific for image downloads."""
        return {
            **self._headers,
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Sec-Fetch-Dest": "image",
            "Sec-Fetch-Mode": "no-cors"
        }

    def _get_download_headers(self) -> Dict[str, str]:
        """Get headers specific for file downloads."""
        return {
            **self._headers,
            "Accept": "application/zip,application/octet-stream",
            "Sec-Fetch-Dest": "download",
            "Sec-Fetch-Mode": "navigate"
        }

    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Perform GET request with browser-like behavior."""
        if not self._session:
            await self.create_session()

        max_retries = kwargs.pop('max_retries', 3)
        retry_delay = kwargs.pop('retry_delay', 1)
        is_image = kwargs.pop('is_image', False)
        is_download = kwargs.pop('is_download', False)
        
        # Set appropriate headers based on request type
        if is_image:
            self._session.headers.update(self._get_image_headers())
        elif is_download:
            self._session.headers.update(self._get_download_headers())
        
        for attempt in range(max_retries):
            try:
                response = await self._session.get(url, **kwargs)
                response.raise_for_status()
                return response
            except Exception as e:
                self._logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(retry_delay * (2 ** attempt))
                await self.create_session()

    async def stream(self, url: str, **kwargs) -> httpx.Response:
        """Stream request with browser-like behavior."""
        kwargs['is_download'] = True
        return await self.get(url, **kwargs)

    async def close(self):
        """Close session."""
        if self._session:
            await self._session.aclose()
            self._session = None