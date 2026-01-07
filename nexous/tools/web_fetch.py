"""
NEXOUS Tool - Web Fetch

웹 페이지 가져오기 도구
"""

from __future__ import annotations

import time
import logging
from typing import Optional
from urllib.parse import urlparse

from .base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class WebFetchTool(BaseTool):
    """웹 페이지 가져오기 도구"""
    
    name = "web_fetch"
    description = "Fetch content from a URL"
    
    TIMEOUT = 30  # seconds
    MAX_SIZE = 1024 * 1024  # 1MB
    
    # 허용된 도메인 (옵션)
    ALLOWED_DOMAINS = None  # None이면 모두 허용
    
    def execute(self, url: str, timeout: int = None) -> ToolResult:
        """
        URL에서 내용 가져오기
        
        Args:
            url: 가져올 URL
            timeout: 타임아웃 (초)
            
        Returns:
            ToolResult
        """
        start_time = time.time()
        timeout = timeout or self.TIMEOUT
        
        # URL 검증
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Invalid URL scheme: {parsed.scheme}",
                    latency_ms=int((time.time() - start_time) * 1000)
                )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Invalid URL: {e}",
                latency_ms=int((time.time() - start_time) * 1000)
            )
        
        try:
            import requests
            
            response = requests.get(
                url,
                timeout=timeout,
                headers={"User-Agent": "NEXOUS/0.1.0"}
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                content = response.text[:self.MAX_SIZE]
                logger.info(f"[WebFetch] {url[:50]}... | {len(content)} chars | {latency_ms}ms")
                
                return ToolResult(
                    success=True,
                    output=content,
                    latency_ms=latency_ms
                )
            else:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"HTTP {response.status_code}",
                    latency_ms=latency_ms
                )
                
        except ImportError:
            return ToolResult(
                success=False,
                output=None,
                error="requests package not installed",
                latency_ms=int((time.time() - start_time) * 1000)
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
                latency_ms=latency_ms
            )
