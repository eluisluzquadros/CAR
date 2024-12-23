# SICAR/http_client.py
"""Async HTTP Client Module using httpx with improved error handling."""

import httpx
import asyncio
from typing import Optional, Dict, Union
import logging
from SICAR.exceptions import (
    UrlNotOkException,
    ConnectionTimeoutException,
    SSLVerificationException,
    SessionClosedException
)

class HttpClient:
    """Async HTTP client using httpx"""
    
    def __init__(self, verify_ssl: bool = False, timeout: float = 30.0):
        self._session: Optional[httpx.AsyncClient] = None
        self._headers = self._get_default_headers()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._verify = verify_ssl
        self._timeout = timeout

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for requests."""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }

    async def create_session(self):
        """Create httpx async session with error handling."""
        try:
            if self._session:
                await self._session.aclose()
            
            limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
            self._session = httpx.AsyncClient(
                verify=self._verify,
                timeout=self._timeout,
                headers=self._headers,
                follow_redirects=True,
                limits=limits
            )
            self._logger.debug("Created new HTTP session")
        except Exception as e:
            self._logger.error(f"Failed to create session: {str(e)}")
            raise

    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Perform GET request with retries and error handling."""
        if not self._session:
            await self.create_session()

        max_retries = kwargs.pop('max_retries', 3)
        retry_delay = kwargs.pop('retry_delay', 1)
        
        for attempt in range(max_retries):
            try:
                response = await self._session.get(url, **kwargs)
                response.raise_for_status()
                return response
                
            except httpx.TimeoutException as e:
                self._logger.warning(f"Attempt {attempt + 1} failed with timeout: {str(e)}")
                if attempt == max_retries - 1:
                    raise ConnectionTimeoutException(url) from e
                    
            except httpx.TLSError as e:
                self._logger.warning(f"Attempt {attempt + 1} failed with SSL error: {str(e)}")
                if attempt == max_retries - 1:
                    raise SSLVerificationException(url) from e
                    
            except Exception as e:
                self._logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                    
            await asyncio.sleep(retry_delay * (attempt + 1))
            await self.create_session()

    async def stream(self, url: str, **kwargs) -> httpx.Response:
        """Create streaming GET request with proper error handling."""
        if not self._session:
            await self.create_session()
            
        try:
            return await self._session.get(url, **kwargs)
        except Exception as e:
            self._logger.error(f"Stream request failed: {str(e)}")
            raise

    def set_headers(self, headers: Optional[Dict[str, str]] = None):
        """Set custom headers with validation."""
        if not headers:
            return
            
        if not isinstance(headers, dict):
            raise ValueError("Headers must be a dictionary")
            
        self._headers.update(headers)
        if self._session:
            self._session.headers.update(headers)

    async def close(self):
        """Close the session safely."""
        if self._session:
            try:
                await self._session.aclose()
                self._session = None
                self._logger.debug("Session closed successfully")
            except Exception as e:
                self._logger.error(f"Error closing session: {str(e)}")
                raise