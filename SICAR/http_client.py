# SICAR/http_client.py
"""Basic HTTP Client Module with direct SSL configuration."""

import requests
from requests.adapters import HTTPAdapter
import urllib3
import logging
import ssl
from typing import Optional, Dict, Union
from pathlib import Path

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class CustomHTTPAdapter(HTTPAdapter):
    """Custom adapter that sets specific SSL configuration"""
    def __init__(self, **kwargs):
        super(CustomHTTPAdapter, self).__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        # Create our own SSL context
        context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS)  # Use TLS protocol
        context.minimum_version = ssl.TLSVersion.TLSv1  # Allow TLS 1.0 and up
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.set_ciphers('ALL:@SECLEVEL=1')  # Use all available ciphers
        
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)

class HttpClient:
    """HTTP client with basic SSL configuration"""
    
    def __init__(self, timeout: float = 30.0):
        self._session = self._create_session()
        self._headers = self._get_default_headers()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._timeout = timeout

    def _get_default_headers(self) -> Dict[str, str]:
        """Get minimal headers."""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Connection": "close"  # Try with close instead of keep-alive
        }

    def _create_session(self) -> requests.Session:
        """Create session with minimal configuration."""
        session = requests.Session()
        adapter = CustomHTTPAdapter(max_retries=3)
        session.mount('https://', adapter)
        session.verify = False
        return session

    def get(self, url: str, **kwargs) -> requests.Response:
        """Make GET request."""
        try:
            response = self._session.get(
                url,
                headers=self._headers,
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
        """Download file."""
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

    def close(self):
        """Close session."""
        if self._session:
            self._session.close()