# SICAR/http_client.py
"""Enhanced HTTP Client Module with session management."""

import requests
from requests.adapters import HTTPAdapter
import urllib3
import logging
from typing import Optional, Dict, Union
from pathlib import Path
import ssl
import time
import random

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class TLSAdapter(HTTPAdapter):
    def __init__(self, ssl_options=0, **kwargs):
        self.ssl_options = ssl_options
        super(TLSAdapter, self).__init__(**kwargs)

    def init_poolmanager(self, *pool_args, **pool_kwargs):
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        
        self.poolmanager = urllib3.PoolManager(
            *pool_args,
            ssl_context=ctx,
            **pool_kwargs
        )

class HttpClient:
    """HTTP client with proper session management"""
    
    def __init__(self, verify_ssl: bool = False, timeout: float = 30.0):
        self._session = None
        self._base_headers = self._get_default_headers()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._timeout = timeout
        self._initialize_session()

    def _get_default_headers(self) -> Dict[str, str]:
        """Get browser-like headers."""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document"
        }

    def _initialize_session(self):
        """Initialize a new session."""
        if self._session:
            self._session.close()
        
        self._session = requests.Session()
        adapter = TLSAdapter(max_retries=3)
        self._session.mount('https://', adapter)
        self._session.verify = False
        self._session.headers.update(self._base_headers)

    def get(self, url: str, **kwargs) -> requests.Response:
        """Perform GET request with proper session handling."""
        if not self._session:
            self._initialize_session()

        try:
            # Prepare headers
            headers = self._base_headers.copy()
            if 'headers' in kwargs:
                headers.update(kwargs.pop('headers'))

            # Add random delay
            time.sleep(random.uniform(0.5, 1.5))

            # Make request
            response = self._session.get(
                url,
                headers=headers,
                timeout=self._timeout,
                verify=False,
                allow_redirects=True,
                **kwargs
            )

            # Debug info
            self._logger.debug(f"URL: {url}")
            self._logger.debug(f"Status Code: {response.status_code}")
            self._logger.debug(f"Headers: {response.headers}")

            response.raise_for_status()
            return response

        except requests.RequestException as e:
            self._logger.error(f"Request failed: {str(e)}")
            # Try to reinitialize session on failure
            self._initialize_session()
            raise

    def get_with_session_check(self, url: str, index_url: str, **kwargs) -> requests.Response:
        """GET with session validation."""
        try:
            # First try direct request
            return self.get(url, **kwargs)
        except:
            # On failure, try to reinitialize session via index page
            self._logger.info("Reinitializing session...")
            self._initialize_session()
            self.get(index_url)  # Get index page to initialize session
            time.sleep(1)  # Small delay
            return self.get(url, **kwargs)  # Retry original request

    def download_file(self, url: str, output_path: Union[str, Path], **kwargs) -> bool:
        """Download file with progress tracking."""
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            response = self.get(url, stream=True, **kwargs)
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
            
        except Exception as e:
            self._logger.error(f"Download failed: {str(e)}")
            if output_path.exists():
                output_path.unlink()
            return False

    def set_headers(self, headers: Optional[Dict[str, str]] = None):
        """Update base headers."""
        if headers:
            self._base_headers.update(headers)
            if self._session:
                self._session.headers.update(headers)

    def close(self):
        """Close the session."""
        if self._session:
            self._session.close()
            self._session = None