"""HTTP Client Module with legacy SSL support."""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
import urllib3
import logging
from typing import Optional, Dict, Union, BinaryIO
import os
from pathlib import Path

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class LegacySSLAdapter(HTTPAdapter):
    """SSL Adapter that supports legacy servers"""
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.load_default_certs()
        context.set_ciphers('DEFAULT@SECLEVEL=1')
        context.options &= ~0x4  # ssl.OP_NO_SSLv3
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)

class HttpClient:
    """HTTP client with legacy SSL support"""
    
    def __init__(self, verify_ssl: bool = False, timeout: float = 30.0):
        self._session = self._create_session()
        self._headers = self._get_default_headers()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._timeout = timeout
        
    def _get_default_headers(self) -> Dict[str, str]:
        """Get browser-like headers."""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }

    def _create_session(self) -> requests.Session:
        """Create session with legacy SSL support."""
        session = requests.Session()
        adapter = LegacySSLAdapter(max_retries=3)
        session.mount('https://', adapter)
        return session

    def get(self, url: str, **kwargs) -> requests.Response:
        """Perform GET request."""
        kwargs.setdefault('timeout', self._timeout)
        kwargs.setdefault('verify', False)
        kwargs.setdefault('headers', self._headers)
        
        try:
            response = self._session.get(url, **kwargs)
            response.raise_for_status()
            return response
        except Exception as e:
            self._logger.error(f"Request failed: {str(e)}")
            raise

    def stream_download(self, url: str, output_path: Union[str, Path], **kwargs) -> bool:
        """Download file with progress tracking."""
        try:
            with self._session.get(
                url,
                stream=True,
                verify=False,
                headers=self._headers,
                timeout=self._timeout,
                **kwargs
            ) as response:
                response.raise_for_status()
                
                # Ensure directory exists
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Download with progress tracking
                total = int(response.headers.get('content-length', 0))
                
                with open(output_path, 'wb') as f:
                    if total:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    else:
                        f.write(response.content)
                        
                return True
                
        except Exception as e:
            self._logger.error(f"Download failed: {str(e)}")
            if output_path.exists():
                output_path.unlink()
            return False

    def set_headers(self, headers: Optional[Dict[str, str]] = None):
        """Set custom headers."""
        if headers:
            self._headers.update(headers)
            self._session.headers.update(headers)

    def close(self):
        """Close the session."""
        if self._session:
            self._session.close()
            self._session = None