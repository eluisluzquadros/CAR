"""
Async HTTP Client Module using aiohttp.
"""

import aiohttp
import asyncio
import ssl
from typing import Optional, Dict
import logging
from functools import wraps

class HttpClient:
    """Async HTTP client with custom SSL configuration"""
    
    def __init__(self, verify_ssl: bool = False, timeout: float = 30.0):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session = None
        self._headers = self._get_default_headers()
        self.verify_ssl = verify_ssl
        
    async def __aenter__(self):
        await self.create_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _get_default_headers(self) -> Dict:
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive'
        }

    async def create_session(self):
        """Create aiohttp session with custom SSL context"""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(
            ssl=ssl_context if not self.verify_ssl else True,
            force_close=True
        )
        
        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=self.timeout,
            headers=self._headers
        )

    async def close(self):
        """Close the session"""
        if self._session:
            await self._session.close()
            
    def set_headers(self, headers: Optional[Dict] = None):
        """Set custom headers"""
        if headers:
            self._headers.update(headers)
            if self._session:
                self._session.headers.update(headers)

    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Async GET request with retries"""
        if not self._session:
            await self.create_session()
            
        max_retries = kwargs.pop('max_retries', 3)
        for attempt in range(max_retries):
            try:
                async with self._session.get(url, **kwargs) as response:
                    response.raise_for_status()
                    return response
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
                continue

    async def stream(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Create streaming GET request"""
        if not self._session:
            await self.create_session()
        return await self._session.get(url, **kwargs)