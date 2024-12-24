# SICAR/http_client.py
"""HTTP Client Module with legacy SSL support."""

import requests
from requests.adapters import HTTPAdapter
import urllib3
import logging
from typing import Optional, Dict, Union
from pathlib import Path
import ssl

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
    """HTTP client with legacy SSL support"""
    
    def __init__(self, verify_ssl: bool = False, timeout: float = 30.0):
        self._session = self._create_session()
        self._base_headers = self._get_default_headers()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._timeout = timeout

    def _get_default_headers(self) -> Dict[str, str]:
        """Get browser-like headers."""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }

    def _create_session(self) -> requests.Session:
        """Create session with legacy SSL support."""
        session = requests.Session()
        adapter = TLSAdapter(max_retries=3)
        session.mount('https://', adapter)
        session.verify = False
        return session

    def get(self, url: str, **kwargs) -> requests.Response:
        """Perform GET request with proper header handling."""
        try:
            # Start with base headers
            headers = self._base_headers.copy()
            
            # Update with any custom headers passed to the method
            if 'headers' in kwargs:
                headers.update(kwargs.pop('headers'))
            
            # Make the request with combined headers
            response = self._session.get(
                url,
                headers=headers,
                timeout=self._timeout,
                verify=False,
                **kwargs
            )
            response.raise_for_status()
            return response
            
        except Exception as e:
            self._logger.error(f"Request failed: {str(e)}")
            raise

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

    def close(self):
        """Close the session."""
        if self._session:
            self._session.close()