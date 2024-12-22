"""
Async HTTP Client Module using aiohttp with custom SSL configuration.
"""

import aiohttp
import asyncio
import ssl
import certifi
from typing import Optional, Dict
import logging
from aiohttp_socks import ProxyConnector

class HttpClient:
    """Async HTTP client with custom SSL configuration"""
    
    def __init__(self, verify_ssl: bool = False, timeout: float = 30.0):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session = None
        self._headers = self._get_default_headers()
        self.verify_ssl = verify_ssl
        self._logger = logging.getLogger(self.__class__.__name__)

    def _get_default_headers(self) -> Dict:
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive'
        }

    async def create_session(self):
        """Create aiohttp session with custom SSL context"""
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        ssl_context.set_ciphers('DEFAULT@SECLEVEL=1')
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(
            ssl=ssl_context,
            force_close=True,
            enable_cleanup_closed=True,
            limit=10
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
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                # Remove parâmetros conflitantes de SSL
                kwargs.pop('ssl', None)
                kwargs.pop('verify_ssl', None)
                
                async with self._session.get(url, **kwargs) as response:
                    await response.read()
                    return response
            except Exception as e:
                last_exception = e
                self._logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    break
                await asyncio.sleep(2 ** attempt)
                
                # Recria a sessão em caso de erro
                await self.close()
                await self.create_session()
                
        raise last_exception

    async def stream(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Create streaming GET request"""
        if not self._session:
            await self.create_session()
        
        # Remove parâmetros conflitantes de SSL
        kwargs.pop('ssl', None)
        kwargs.pop('verify_ssl', None)
        
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