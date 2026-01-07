"""
NEXOUS LLM - OpenAI Client

LEVEL 2:
- gpt-4o 모델만 허용
- OPENAI_API_KEY 환경변수 사용
- LLMClient 인터페이스 구현
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


# 허용 모델
ALLOWED_OPENAI_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]


class OpenAIClient(LLMClient):
    """
    OpenAI LLM Client
    
    LEVEL 2 구현
    """
    
    DEFAULT_MODEL = "gpt-4o"
    DEFAULT_TIMEOUT = 60
    
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._client = None
    
    @property
    def provider(self) -> str:
        return LLMProvider.OPENAI.value
    
    def is_available(self) -> bool:
        """API 키 존재 여부"""
        return bool(self._api_key)
    
    @property
    def client(self):
        """OpenAI Client (Lazy initialization)"""
        if self._client is None:
            if not self._api_key:
                raise LLMClientError(
                    "OPENAI_API_KEY not set",
                    provider=self.provider,
                    recoverable=False,
                )
            
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self._api_key,
                    timeout=self.DEFAULT_TIMEOUT,
                )
            except ImportError:
                raise LLMClientError(
                    "openai package not installed. Run: pip install openai",
                    provider=self.provider,
                    recoverable=False,
                )
        
        return self._client
    
    def generate(
        self,
        messages: List[LLMMessage],
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: int = 60,
        **kwargs
    ) -> LLMResponse:
        """OpenAI 응답 생성"""
        
        model = model or self.DEFAULT_MODEL
        
        # 모델 검증
        if model not in ALLOWED_OPENAI_MODELS:
            raise LLMClientError(
                f"Model '{model}' not allowed. Allowed: {ALLOWED_OPENAI_MODELS}",
                provider=self.provider,
                model=model,
                recoverable=False,
            )
        
        start_time = time.time()
        
        try:
            # 메시지 변환
            api_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            # API 호출
            response = self.client.chat.completions.create(
                model=model,
                messages=api_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # 응답 파싱
            content = response.choices[0].message.content or ""
            finish_reason = response.choices[0].finish_reason or "stop"
            
            tokens_input = response.usage.prompt_tokens if response.usage else 0
            tokens_output = response.usage.completion_tokens if response.usage else 0
            
            logger.info(
                f"[OpenAIClient] {model} | "
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
                finish_reason=finish_reason,
            )
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            
            recoverable = "rate" in error_msg.lower() or "timeout" in error_msg.lower()
            
            logger.error(f"[OpenAIClient] Error: {error_msg}")
            
            raise LLMClientError(
                error_msg,
                provider=self.provider,
                model=model,
                recoverable=recoverable,
                original_error=e,
            )
