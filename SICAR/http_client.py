"""
Async HTTP Client Module using aiohttp with proxy support.
"""

import aiohttp
import asyncio
import ssl
from typing import Optional, Dict
import logging
from aiohttp_socks import ProxyConnector

class HttpClient:
    """Async HTTP client with proxy support and SSL configuration"""
    
    def __init__(self, verify_ssl: bool = False, timeout: float = 30.0):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session = None
        self._headers = self._get_default_headers()
        self._logger = logging.getLogger(self.__class__.__name__)
        
        # Create an SSL context that accepts all certificates
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        # Support older protocols
        self.ssl_context.set_ciphers('DEFAULT:@SECLEVEL=1')

    def _get_default_headers(self) -> Dict:
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

    async def create_session(self):
        """Create aiohttp session with custom SSL context"""
        connector = aiohttp.TCPConnector(
            ssl=self.ssl_context,
            force_close=True
        )
        
        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=self.timeout,
            headers=self._headers,
            trust_env=True
        )

    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Perform GET request with retries"""
        if not self._session:
            await self.create_session()

        max_retries = kwargs.pop('max_retries', 3)
        retry_delay = kwargs.pop('retry_delay', 2)
        
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
                await self.close()
                await self.create_session()

    async def stream(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Create streaming GET request"""
        if not self._session:
            await self.create_session()
        return await self._session.get(url, **kwargs)

    def set_headers(self, headers: Optional[Dict] = None):
        """Set custom headers"""
        if headers:
            self._headers.update(headers)
            if self._session:
                self._session.headers.update(headers)

    async def close(self):
        """Close the session"""
        if self._session:
            await self._session.close()
            self._session = None