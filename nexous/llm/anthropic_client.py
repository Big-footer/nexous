"""
NEXOUS LLM - Anthropic Client

Anthropic Claude API 클라이언트

LEVEL 2:
- Claude 3.5 Sonnet, Claude 3 Opus 지원
- ANTHROPIC_API_KEY 환경변수 필요
"""

from __future__ import annotations

import os
import time
import logging
from typing import List, Optional

from .base import (
    LLMClient,
    LLMMessage,
    LLMResponse,
    LLMClientError,
    LLMProvider,
)

logger = logging.getLogger(__name__)


# 허용된 모델
ALLOWED_ANTHROPIC_MODELS = [
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-latest",
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
]


class AnthropicClient(LLMClient):
    """
    Anthropic Claude Client
    
    ANTHROPIC_API_KEY 환경변수 필요
    """
    
    def __init__(self):
        self._client = None
        self._api_key = os.getenv("ANTHROPIC_API_KEY", "")
    
    @property
    def provider(self) -> str:
        return LLMProvider.ANTHROPIC.value
    
    @property
    def client(self):
        """Anthropic Client (Lazy initialization)"""
        if self._client is None:
            if not self._api_key:
                raise LLMClientError(
                    "ANTHROPIC_API_KEY not set",
                    provider=self.provider,
                    recoverable=False,
                )
            
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self._api_key)
            except ImportError:
                raise LLMClientError(
                    "anthropic package not installed. Run: pip install anthropic",
                    provider=self.provider,
                    recoverable=False,
                )
        
        return self._client
    
    def is_available(self) -> bool:
        """API 키 존재 여부"""
        return bool(self._api_key)
    
    def generate(
        self,
        messages: List[LLMMessage],
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: int = 60,
        **kwargs
    ) -> LLMResponse:
        """Claude 응답 생성"""
        
        # 모델 검증
        if model not in ALLOWED_ANTHROPIC_MODELS:
            raise LLMClientError(
                f"Model '{model}' not allowed. Allowed: {ALLOWED_ANTHROPIC_MODELS}",
                provider=self.provider,
                model=model,
                recoverable=False,
            )
        
        start_time = time.time()
        
        try:
            # 메시지 변환 (system 분리)
            system_content = ""
            api_messages = []
            
            for msg in messages:
                if msg.role == "system":
                    system_content = msg.content
                else:
                    api_messages.append({
                        "role": msg.role,
                        "content": msg.content,
                    })
            
            # API 호출
            response = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_content if system_content else None,
                messages=api_messages,
                timeout=timeout,
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # 응답 파싱
            content = ""
            if response.content:
                content = response.content[0].text
            
            tokens_input = response.usage.input_tokens if response.usage else 0
            tokens_output = response.usage.output_tokens if response.usage else 0
            
            logger.info(
                f"[AnthropicClient] {model} | "
                f"tokens: {tokens_input}+{tokens_output}={tokens_input+tokens_output} | "
                f"latency: {latency_ms}ms"
            )
            
            return LLMResponse(
                content=content,
                model=model,
                provider=self.provider,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                latency_ms=latency_ms,
                finish_reason=response.stop_reason or "stop",
            )
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            
            # 복구 가능 여부 판단
            recoverable = "rate" in error_msg.lower() or "timeout" in error_msg.lower()
            
            logger.error(f"[AnthropicClient] Error: {error_msg}")
            
            raise LLMClientError(
                error_msg,
                provider=self.provider,
                model=model,
                recoverable=recoverable,
                original_error=e,
            )
