"""
Web tool for agents
Allows agents to make HTTP requests
"""

import logging
import json
import time
from typing import Dict, Any, Optional
from urllib.parse import urlparse

# Use the requests library for HTTP
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logging.warning("Requests library not available. Install with pip install requests")

logger = logging.getLogger(__name__)

class WebTool:
    """Tool for making web requests"""
    
    def __init__(self, timeout: int = 30, user_agent: str = None):
        """Initialize the web tool"""
        self.timeout = timeout
        self.user_agent = user_agent or "CPAS3-Agent/1.0"
        self._session = None
        
        if not REQUESTS_AVAILABLE:
            logger.error("Requests library not available. Install with pip install requests")
        else:
            self._session = requests.Session()
            self._session.headers.update({"User-Agent": self.user_agent})
            logger.info("Web tool initialized")
    
    def is_available(self) -> bool:
        """Check if the web tool is available"""
        return REQUESTS_AVAILABLE and self._session is not None
    
    def get(self, url: str, headers: Dict[str, str] = None, 
            params: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Make a GET request to a URL
        
        Args:
            url: The URL to request
            headers: Optional HTTP headers
            params: Optional query parameters
            
        Returns:
            Dictionary with request results
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "Web tool not available"
            }
            
        try:
            logger.info(f"Making GET request to: {url}")
            
            # Verify URL (basic security check)
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError(f"Invalid URL: {url}")
                
            # Make the request with timing
            start_time = time.time()
            response = self._session.get(
                url, 
                headers=headers,
                params=params,
                timeout=self.timeout
            )
            duration = time.time() - start_time
            
            # Build result
            result = {
                "url": url,
                "status_code": response.status_code,
                "success": response.status_code >= 200 and response.status_code < 300,
                "duration": duration,
                "headers": dict(response.headers),
                "content_type": response.headers.get("Content-Type", "")
            }
            
            # Try to parse content based on content type
            content_type = response.headers.get("Content-Type", "").lower()
            
            if "application/json" in content_type:
                try:
                    result["data"] = response.json()
                except:
                    result["text"] = response.text
            elif "text/" in content_type:
                result["text"] = response.text
            else:
                # For binary content, just indicate the size
                result["content_length"] = len(response.content)
                
            logger.info(f"GET request completed with status: {response.status_code}")
            return result
            
        except Exception as e:
            logger.error(f"Error making GET request: {str(e)}")
            return {
                "url": url,
                "success": False,
                "error": str(e)
            }
    
    def post(self, url: str, data: Any = None, 
            json_data: Any = None,
            headers: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Make a POST request to a URL
        
        Args:
            url: The URL to request
            data: Form data to send
            json_data: JSON data to send
            headers: Optional HTTP headers
            
        Returns:
            Dictionary with request results
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "Web tool not available"
            }
            
        try:
            logger.info(f"Making POST request to: {url}")
            
            # Verify URL (basic security check)
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError(f"Invalid URL: {url}")
                
            # Make the request with timing
            start_time = time.time()
            response = self._session.post(
                url, 
                data=data,
                json=json_data,
                headers=headers,
                timeout=self.timeout
            )
            duration = time.time() - start_time
            
            # Build result
            result = {
                "url": url,
                "status_code": response.status_code,
                "success": response.status_code >= 200 and response.status_code < 300,
                "duration": duration,
                "headers": dict(response.headers),
                "content_type": response.headers.get("Content-Type", "")
            }
            
            # Try to parse content based on content type
            content_type = response.headers.get("Content-Type", "").lower()
            
            if "application/json" in content_type:
                try:
                    result["data"] = response.json()
                except:
                    result["text"] = response.text
            elif "text/" in content_type:
                result["text"] = response.text
            else:
                # For binary content, just indicate the size
                result["content_length"] = len(response.content)
                
            logger.info(f"POST request completed with status: {response.status_code}")
            return result
            
        except Exception as e:
            logger.error(f"Error making POST request: {str(e)}")
            return {
                "url": url,
                "success": False,
                "error": str(e)
            }
