# SICAR/http_client.py
"""HTTP Client Module with legacy SSL support."""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
from urllib3.poolmanager import PoolManager
import urllib3
import logging
from typing import Optional, Dict, Union, BinaryIO
import os
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
        # Set the SSL options we want
        ctx.options |= self.ssl_options
        
        # These configurations MUST be done in this order
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        
        self.poolmanager = PoolManager(*pool_args,
                                     ssl_context=ctx,
                                     **pool_kwargs)

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
            "Upgrade-Insecure-Requests": "1",
            "DNT": "1"
        }

    def _create_session(self) -> requests.Session:
        """Create session with legacy SSL support."""
        session = requests.Session()
        
        # Create adapter with all SSL options we might need
        adapter = TLSAdapter(
            ssl_options=ssl.OP_NO_TLSv1_3 |  # Disable TLS 1.3
                       ~ssl.OP_NO_TLSv1 |   # Enable TLS 1.0
                       ~ssl.OP_NO_TLSv1_1 | # Enable TLS 1.1
                       ~ssl.OP_NO_SSLv3,    # Enable SSL 3
            pool_maxsize=100,
            max_retries=3,
            pool_block=False
        )
        
        session.mount('https://', adapter)
        session.verify = False
        return session

    def get(self, url: str, **kwargs) -> requests.Response:
        """Perform GET request."""
        kwargs.setdefault('timeout', self._timeout)
        kwargs.setdefault('verify', False)
        
        # Set specific headers for the request type
        headers = self._headers.copy()
        if url.endswith('.jpg') or url.endswith('.png') or 'captcha' in url.lower():
            headers.update({
                'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors'
            })
        kwargs.setdefault('headers', headers)
        
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

    def close(self):
        """Close the session."""
        if self._session:
            self._session.close()
            self._session = None