# SICAR/http_client.py
"""Async HTTP Client Module specifically configured for SICAR website."""

import httpx
import asyncio
import ssl
import certifi
from typing import Optional, Dict, Union
import logging
from SICAR.exceptions import (
    UrlNotOkException,
    ConnectionTimeoutException,
    SSLVerificationException,
    SessionClosedException
)

class HttpClient:
    """Async HTTP client customized for SICAR website access"""
    
    def __init__(self, verify_ssl: bool = False, timeout: float = 30.0):
        self._session: Optional[httpx.AsyncClient] = None
        self._headers = self._get_default_headers()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._verify = verify_ssl
        self._timeout = timeout
        
        # Create SSL context specifically for SICAR
        self._ssl_context = self._create_ssl_context()

    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create a custom SSL context for SICAR website."""
        context = ssl.create_default_context(cafile=certifi.where())
        context.set_ciphers('DEFAULT@SECLEVEL=1')  # Allow older ciphers
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        # Enable all SSL/TLS versions
        context.options &= ~ssl.OP_NO_SSLv3
        context.options &= ~ssl.OP_NO_TLSv1
        context.options &= ~ssl.OP_NO_TLSv1_1
        return context

    def _get_default_headers(self) -> Dict[str, str]:
        """Get headers specifically formatted for SICAR website."""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Cache-Control": "max-age=0"
        }

    async def create_session(self):
        """Create session with SICAR-specific configurations."""
        try:
            if self._session:
                await self._session.aclose()
            
            # Custom transport with retry logic
            transport = httpx.AsyncHTTPTransport(
                verify=False,
                retries=3,
                trust_env=True,
                http2=False  # Disable HTTP/2 as it might cause issues
            )
            
            self._session = httpx.AsyncClient(
                verify=False,
                timeout=self._timeout,
                headers=self._headers,
                follow_redirects=True,
                transport=transport
            )
            self._logger.debug("Created new HTTP session")
        except Exception as e:
            self._logger.error(f"Failed to create session: {str(e)}")
            raise

    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Perform GET request with SICAR-specific retry logic."""
        if not self._session:
            await self.create_session()

        max_retries = kwargs.pop('max_retries', 3)
        retry_delay = kwargs.pop('retry_delay', 2)  # Increased delay
        
        for attempt in range(max_retries):
            try:
                response = await self._session.get(url, **kwargs)
                response.raise_for_status()
                return response
                
            except httpx.TimeoutException as e:
                self._logger.warning(f"Attempt {attempt + 1} failed with timeout: {str(e)}")
                if attempt == max_retries - 1:
                    raise ConnectionTimeoutException(url) from e
                    
            except httpx.HTTPStatusError as e:
                self._logger.warning(f"Attempt {attempt + 1} failed with HTTP error: {str(e)}")
                if attempt == max_retries - 1:
                    raise UrlNotOkException(url) from e
                    
            except Exception as e:
                self._logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                    
            # Exponential backoff
            await asyncio.sleep(retry_delay * (2 ** attempt))
            await self.create_session()

    async def stream(self, url: str, **kwargs) -> httpx.Response:
        """Stream request with proper error handling for SICAR downloads."""
        if not self._session:
            await self.create_session()
            
        try:
            response = await self._session.get(url, **kwargs)
            response.raise_for_status()
            return response
        except Exception as e:
            self._logger.error(f"Stream request failed: {str(e)}")
            raise

    def set_headers(self, headers: Optional[Dict[str, str]] = None):
        """Update headers while preserving essential SICAR headers."""
        if not headers:
            return
            
        if not isinstance(headers, dict):
            raise ValueError("Headers must be a dictionary")
            
        # Preserve essential SICAR headers
        essential_headers = {
            k: v for k, v in self._headers.items() 
            if k in ['User-Agent', 'Accept-Language', 'Connection']
        }
        
        self._headers.update(headers)
        self._headers.update(essential_headers)
        
        if self._session:
            self._session.headers.update(self._headers)

    async def close(self):
        """Safely close the session."""
        if self._session:
            try:
                await self._session.aclose()
                self._session = None
                self._logger.debug("Session closed successfully")
            except Exception as e:
                self._logger.error(f"Error closing session: {str(e)}")
                raise