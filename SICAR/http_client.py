# SICAR/http_client.py
"""Async HTTP Client Module using aiohttp with custom SSL configuration."""

import aiohttp
import asyncio
import ssl
from typing import Optional, Dict
import logging
from aiohttp.client import ClientTimeout

class HttpClient:
    """Async HTTP client using aiohttp"""
    
    def __init__(self, verify_ssl: bool = False, timeout: float = 30.0):
        self._session: Optional[aiohttp.ClientSession] = None
        self._headers = self._get_default_headers()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._timeout = ClientTimeout(total=timeout)
        self._ssl_context = self._create_ssl_context()

    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create a custom SSL context that accepts older protocols."""
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        # Important: must disable hostname check before setting verify mode
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.set_ciphers('DEFAULT:@SECLEVEL=1')
        
        # Enable older protocols
        context.options &= ~ssl.OP_NO_TLSv1
        context.options &= ~ssl.OP_NO_TLSv1_1
        context.options &= ~ssl.OP_NO_SSLv3
        
        return context

    def _get_default_headers(self) -> Dict[str, str]:
        """Get browser-like headers."""
        return {
            "Host": "consultapublica.car.gov.br",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }

    async def create_session(self):
        """Create aiohttp session with custom SSL context."""
        try:
            if self._session:
                await self._session.close()
                
            conn = aiohttp.TCPConnector(
                ssl=self._ssl_context,
                force_close=True,
                enable_cleanup_closed=True,
                ttl_dns_cache=300
            )
            
            self._session = aiohttp.ClientSession(
                connector=conn,
                timeout=self._timeout,
                headers=self._headers,
                trust_env=True
            )
        except Exception as e:
            self._logger.error(f"Failed to create session: {str(e)}")
            raise

    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Perform GET request with retries."""
        if not self._session:
            await self.create_session()

        max_retries = kwargs.pop('max_retries', 3)
        retry_delay = kwargs.pop('retry_delay', 1)
        
        for attempt in range(max_retries):
            try:
                async with self._session.get(url, **kwargs) as response:
                    await response.read()
                    return response
            except Exception as e:
                self._logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(retry_delay * (attempt + 1))
                await self.create_session()

    async def stream(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Create streaming GET request."""
        if not self._session:
            await self.create_session()
            
        return await self._session.get(url, **kwargs)

    def set_headers(self, headers: Optional[Dict[str, str]] = None):
        """Set custom headers."""
        if headers:
            self._headers.update(headers)
            if self._session:
                self._session.headers.update(headers)

    async def close(self):
        """Close the session."""
        if self._session:
            try:
                await self._session.close()
                self._session = None
            except Exception as e:
                self._logger.error(f"Error closing session: {str(e)}")
                raise