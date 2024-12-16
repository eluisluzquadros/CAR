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

def retry_with_backoff(max_retries: int = 3, initial_delay: float = 1.0):
    """Decorator for implementing retry logic with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for retry in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if retry < max_retries - 1:
                        sleep_time = delay * (2 ** retry) + random.uniform(0, 1)
                        time.sleep(sleep_time)
                    continue
            raise last_exception
        return wrapper
    return decorator

class HttpClient:
    """Custom HTTP client with robust error handling"""
    
    def __init__(self, verify_ssl: bool = True, timeout: float = 30.0):
        self.session = self._create_session(verify_ssl, timeout)
    
    def _create_session(self, verify_ssl: bool, timeout: float) -> httpx.Client:
        """Create an HTTP session with appropriate SSL context"""
        if verify_ssl:
            try:
                ssl_context = ssl.create_default_context(cafile=certifi.where())
                ssl_context.verify_mode = ssl.CERT_REQUIRED
                ssl_context.options |= ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3
                
                return httpx.Client(
                    verify=ssl_context,
                    timeout=timeout,
                    follow_redirects=True
                )
            except:
                # Fallback to no verification if SSL context creation fails
                pass
        
        return httpx.Client(
            verify=False,
            timeout=timeout,
            follow_redirects=True
        )
    
    def set_headers(self, headers: Optional[Dict] = None):
        """Set custom headers for the session"""
        default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*",
            "Connection": "keep-alive"
        }
        self.session.headers.update(headers or default_headers)
    
    @retry_with_backoff()
    def get(self, url: str, **kwargs):
        """Perform GET request with retry logic"""
        response = self.session.get(url, **kwargs)
        response.raise_for_status()
        return response
    
    def stream(self, url: str, **kwargs):
        """Create a streaming response"""
        return self.session.stream("GET", url, **kwargs)