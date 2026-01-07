"""
NEXOUS Provider - OpenAI

단일 LLM Provider 구현
- 모델: gpt-4o (고정)
- retry / timeout / token logging
"""

from __future__ import annotations

import os
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """LLM 응답"""
    content: str
    tokens_input: int
    tokens_output: int
    tokens_total: int
    latency_ms: int
    model: str
    provider: str = "openai"


class OpenAIProvider:
    """
    OpenAI LLM Provider
    
    LEVEL 1: 플랫폼 안정화
    - 단일 모델 (gpt-4o)
    - retry / timeout
    - token logging
    """
    
    DEFAULT_MODEL = "gpt-4o"
    MAX_RETRIES = 3
    TIMEOUT = 60  # seconds
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or self.DEFAULT_MODEL
        self._client = None
        
        if not self.api_key:
            logger.warning("[OpenAI] API key not found. Set OPENAI_API_KEY environment variable.")
    
    @property
    def client(self):
        """Lazy initialization of OpenAI client"""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key, timeout=self.TIMEOUT)
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        return self._client
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = None,
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> LLMResponse:
        """
        LLM 채팅 호출
        
        Args:
            messages: [{"role": "user", "content": "..."}]
            system_prompt: 시스템 프롬프트
            temperature: 온도 (0.0 ~ 1.0)
            max_tokens: 최대 토큰 수
            
        Returns:
            LLMResponse
        """
        # 메시지 구성
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)
        
        # Retry 로직
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                start_time = time.time()
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=full_messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                # 토큰 사용량
                usage = response.usage
                tokens_input = usage.prompt_tokens if usage else 0
                tokens_output = usage.completion_tokens if usage else 0
                tokens_total = usage.total_tokens if usage else 0
                
                # 응답 내용
                content = response.choices[0].message.content or ""
                
                logger.info(
                    f"[OpenAI] {self.model} | "
                    f"tokens: {tokens_input}+{tokens_output}={tokens_total} | "
                    f"latency: {latency_ms}ms"
                )
                
                return LLMResponse(
                    content=content,
                    tokens_input=tokens_input,
                    tokens_output=tokens_output,
                    tokens_total=tokens_total,
                    latency_ms=latency_ms,
                    model=self.model,
                    provider="openai"
                )
                
            except Exception as e:
                last_error = e
                logger.warning(f"[OpenAI] Attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        raise RuntimeError(f"OpenAI API failed after {self.MAX_RETRIES} retries: {last_error}")
