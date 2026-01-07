"""
NEXOUS Core - Retry Policy

Agent/Tool 재시도 정책
"""

from __future__ import annotations

import time
import logging
from typing import Callable, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """재시도 설정"""
    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 30.0  # seconds
    exponential: bool = True
    retry_on_errors: tuple = (Exception,)


class RetryPolicy:
    """
    재시도 정책
    
    Tool 실패 시 자동 재시도
    """
    
    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
    
    def execute_with_retry(
        self,
        func: Callable,
        *args,
        on_retry: Callable = None,
        **kwargs
    ) -> Any:
        """
        재시도와 함께 함수 실행
        
        Args:
            func: 실행할 함수
            *args: 함수 인자
            on_retry: 재시도 시 호출할 콜백 (attempt, error)
            **kwargs: 함수 키워드 인자
            
        Returns:
            함수 실행 결과
        """
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                return func(*args, **kwargs)
                
            except self.config.retry_on_errors as e:
                last_error = e
                
                if attempt < self.config.max_retries - 1:
                    delay = self._calculate_delay(attempt)
                    
                    logger.warning(
                        f"[Retry] Attempt {attempt + 1}/{self.config.max_retries} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    
                    if on_retry:
                        on_retry(attempt + 1, e)
                    
                    time.sleep(delay)
                else:
                    logger.error(
                        f"[Retry] All {self.config.max_retries} attempts failed. Last error: {e}"
                    )
        
        raise last_error
    
    def _calculate_delay(self, attempt: int) -> float:
        """지연 시간 계산"""
        if self.config.exponential:
            delay = self.config.base_delay * (2 ** attempt)
        else:
            delay = self.config.base_delay
        
        return min(delay, self.config.max_delay)


class ToolRetryPolicy(RetryPolicy):
    """Tool 전용 재시도 정책"""
    
    def __init__(self):
        super().__init__(RetryConfig(
            max_retries=3,
            base_delay=0.5,
            max_delay=5.0,
            exponential=True
        ))


class LLMRetryPolicy(RetryPolicy):
    """LLM 전용 재시도 정책"""
    
    def __init__(self):
        super().__init__(RetryConfig(
            max_retries=3,
            base_delay=2.0,
            max_delay=30.0,
            exponential=True
        ))
