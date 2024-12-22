"""
HTTP Client Module using requests with robust SSL handling.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from typing import Optional, Dict
import logging

class HttpClient:
    def __init__(self, verify_ssl: bool = False, timeout: float = 30.0):
        self.timeout = timeout
        self.session = self._create_session()
        self._set_default_headers()
        self._logger = logging.getLogger(self.__class__.__name__)

    def _create_session(self) -> requests.Session:
        """Create session with retry strategy"""
        session = requests.Session()
        
        # Configurar retry
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        
        # Criar adapter com retry
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10
        )
        
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.verify = False
        
        return session

    def _set_default_headers(self):
        """Set default headers"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
        })

    def set_headers(self, headers: Optional[Dict] = None):
        """Set custom headers"""
        if headers:
            self.session.headers.update(headers)

    def get(self, url: str, **kwargs):
        """Make GET request"""
        kwargs.setdefault('timeout', self.timeout)
        response = self.session.get(url, **kwargs)
        response.raise_for_status()
        return response

    def stream(self, url: str, **kwargs):
        """Make streaming GET request"""
        kwargs.setdefault('timeout', self.timeout)
        kwargs.setdefault('stream', True)
        return self.session.get(url, **kwargs)

    def close(self):
        """Close the session"""
        self.session.close()