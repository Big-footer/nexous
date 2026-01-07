"""
NEXOUS LLM - Router

정책 기반 LLM 선택 및 호출

LEVEL 2 핵심:
- LLMPolicy에 따라 primary/retry/fallback 수행
- 모든 시도(성공/실패/폴백)를 TraceWriter에 기록
- Agent만 Router를 호출한다
- Runner는 LLM을 전혀 알지 못한다
"""

from __future__ import annotations

import time
import logging
import json
from typing import List, Dict, Any, Optional, Callable

from .base import (
    LLMMessage,
    LLMResponse,
    LLMPolicy,
    LLMClientError,
    LLMAllProvidersFailedError,
)
from .registry import LLMRegistry

logger = logging.getLogger(__name__)


class LLMRouter:
    """
    LLM Router
    
    LLMPolicy를 해석하여 적절한 Provider/Model을 선택하고 호출한다.
    
    책임:
    1. Primary 호출 시도
    2. 실패 시 retry (지수 백오프)
    3. 모든 retry 실패 시 fallback 순서대로 시도
    4. 모든 시도를 trace_callback에 기록
    """
    
    def __init__(
        self,
        policy: LLMPolicy,
        trace_callback: Optional[Callable] = None,
        agent_id: str = "",
    ):
        """
        Args:
            policy: LLM 선택 정책
            trace_callback: TraceWriter.log_step 콜백
            agent_id: Agent ID (trace용)
        """
        self.policy = policy
        self.trace_callback = trace_callback
        self.agent_id = agent_id
        self._attempts: List[Dict[str, Any]] = []
    
    def route(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        **kwargs
    ) -> LLMResponse:
        """
        정책에 따라 LLM 호출
        
        1. Primary 시도 (retry 포함)
        2. 실패 시 fallback 순서대로 시도
        3. 모든 시도 기록
        
        Args:
            messages: LLM 메시지
            temperature: 온도
            max_tokens: 최대 토큰
            
        Returns:
            LLMResponse
            
        Raises:
            LLMAllProvidersFailedError: 모든 Provider 실패
        """
        self._attempts = []
        
        # 1. Primary 시도
        primary_provider, primary_model = self.policy.get_provider_model(self.policy.primary)
        
        response = self._try_with_retry(
            provider=primary_provider,
            model=primary_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            is_primary=True,
            **kwargs
        )
        
        if response:
            return response
        
        # 2. Fallback 시도
        for fallback_spec in self.policy.fallback:
            fallback_provider, fallback_model = self.policy.get_provider_model(fallback_spec)
            
            response = self._try_with_retry(
                provider=fallback_provider,
                model=fallback_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                is_primary=False,
                fallback_from=self.policy.primary,
                **kwargs
            )
            
            if response:
                return response
        
        # 3. 모든 시도 실패
        self._log_all_failed()
        
        raise LLMAllProvidersFailedError(
            f"All LLM providers failed. Attempts: {len(self._attempts)}",
            attempts=self._attempts,
        )
    
    def _try_with_retry(
        self,
        provider: str,
        model: str,
        messages: List[LLMMessage],
        temperature: float,
        max_tokens: int,
        is_primary: bool,
        fallback_from: Optional[str] = None,
        **kwargs
    ) -> Optional[LLMResponse]:
        """
        Retry 포함 호출 시도
        
        Returns:
            성공 시 LLMResponse, 실패 시 None
        """
        retry_count = self.policy.retry if is_primary else 1
        
        for attempt in range(1, retry_count + 1):
            try:
                # Client 획득
                client = LLMRegistry.get(provider)
                
                # 사용 가능 여부 확인
                if not client.is_available():
                    raise LLMClientError(
                        f"{provider} API key not set",
                        provider=provider,
                        recoverable=False,
                    )
                
                # LLM 호출
                start_time = time.time()
                
                response = client.generate(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=self.policy.timeout,
                    **kwargs
                )
                
                # 폴백 정보 추가
                response.attempt = attempt
                if fallback_from:
                    response.fallback_from = fallback_from
                
                # 성공 기록
                self._record_attempt(
                    provider=provider,
                    model=model,
                    attempt=attempt,
                    success=True,
                    response=response,
                    is_fallback=fallback_from is not None,
                )
                
                # Trace 기록
                self._log_llm_step(
                    provider=provider,
                    model=model,
                    response=response,
                    is_fallback=fallback_from is not None,
                    fallback_from=fallback_from,
                )
                
                return response
                
            except LLMClientError as e:
                # 실패 기록
                self._record_attempt(
                    provider=provider,
                    model=model,
                    attempt=attempt,
                    success=False,
                    error=str(e),
                    recoverable=e.recoverable,
                    is_fallback=fallback_from is not None,
                )
                
                # 복구 불가능하면 즉시 종료
                if not e.recoverable:
                    logger.warning(
                        f"[LLMRouter] {provider}/{model} unrecoverable error: {e}"
                    )
                    break
                
                # Retry 대기
                if attempt < retry_count:
                    delay = self.policy.retry_delay * (2 ** (attempt - 1))
                    logger.info(
                        f"[LLMRouter] {provider}/{model} attempt {attempt} failed, "
                        f"retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
        
        return None
    
    def _record_attempt(
        self,
        provider: str,
        model: str,
        attempt: int,
        success: bool,
        response: Optional[LLMResponse] = None,
        error: Optional[str] = None,
        recoverable: bool = True,
        is_fallback: bool = False,
    ):
        """시도 기록"""
        record = {
            "provider": provider,
            "model": model,
            "attempt": attempt,
            "success": success,
            "is_fallback": is_fallback,
            "timestamp": time.time(),
        }
        
        if response:
            record["tokens"] = response.tokens_total
            record["latency_ms"] = response.latency_ms
        
        if error:
            record["error"] = error
            record["recoverable"] = recoverable
        
        self._attempts.append(record)
    
    def _log_llm_step(
        self,
        provider: str,
        model: str,
        response: LLMResponse,
        is_fallback: bool = False,
        fallback_from: Optional[str] = None,
    ):
        """TraceWriter에 LLM step 기록"""
        if not self.trace_callback:
            return
        
        # 입력 요약
        input_summary = f"LLM call to {provider}/{model}"
        if is_fallback:
            input_summary += f" (fallback from {fallback_from})"
        
        # 출력 요약
        output_summary = response.content[:200]
        if len(response.content) > 200:
            output_summary += "..."
        
        metadata = {
            "provider": provider,
            "model": model,
            "tokens_input": response.tokens_input,
            "tokens_output": response.tokens_output,
            "latency_ms": response.latency_ms,
            "finish_reason": response.finish_reason,
            "attempt": response.attempt,
        }
        
        if is_fallback:
            metadata["is_fallback"] = True
            metadata["fallback_from"] = fallback_from
        
        self.trace_callback(
            agent_id=self.agent_id,
            step_type="LLM",
            status="OK",
            payload={
                "input_summary": input_summary,
                "output_summary": output_summary,
            },
            metadata=metadata,
        )
    
    def _log_all_failed(self):
        """모든 시도 실패 기록"""
        if not self.trace_callback:
            return
        
        self.trace_callback(
            agent_id=self.agent_id,
            step_type="LLM",
            status="ERROR",
            payload={
                "error": "All LLM providers failed",
                "attempts": len(self._attempts),
            },
            metadata={
                "attempts_detail": self._attempts,
            },
        )
    
    @property
    def attempts(self) -> List[Dict[str, Any]]:
        """시도 기록 반환"""
        return self._attempts.copy()
