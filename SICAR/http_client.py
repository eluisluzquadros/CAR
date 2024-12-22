"""
HTTP Client Module.

This module provides a custom HTTP client with robust error handling and retry mechanisms.
"""

import ssl
import httpx
import certifi
from typing import Optional, Dict
import time
import random
from functools import wraps
import urllib3

def retry_with_backoff(max_retries: int = 3, initial_delay: float = 1.0):
    """Decorator for implementing retry logic with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for retry in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if retry < max_retries - 1:
                        sleep_time = initial_delay * (2 ** retry) + random.uniform(0, 1)
                        time.sleep(sleep_time)
            raise last_exception
        return wrapper
    return decorator

class HttpClient:
    """Custom HTTP client with robust error handling"""
    
    def __init__(self, verify_ssl: bool = False, timeout: float = 30.0):
        self.session = self._create_session(verify_ssl, timeout)
        self._set_default_headers()
    
    def _create_session(self, verify_ssl: bool, timeout: float) -> httpx.Client:
        """Create an HTTP session with appropriate SSL context"""
        # Desabilitar avisos de SSL inseguro
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Criar o transporte HTTP
        transport = httpx.HTTPTransport(
            verify=False,
            retries=3
        )
        
        # Criar o cliente com configurações apropriadas
        return httpx.Client(
            transport=transport,
            timeout=timeout,
            follow_redirects=True,
            verify=False
        )
    
    def _set_default_headers(self):
        """Set default headers for all requests"""
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive"
        })
    
    def set_headers(self, headers: Optional[Dict] = None):
        """Set custom headers for the session"""
        if headers:
            self.session.headers.update(headers)
    
    @retry_with_backoff(max_retries=3)
    def get(self, url: str, **kwargs):
        """Perform GET request with retry logic"""
        response = self.session.get(url, **kwargs)
        response.raise_for_status()
        return response
    
    def stream(self, url: str, **kwargs):
        """Create a streaming response"""
        return self.session.stream("GET", url, **kwargs)