"""
NEXOUS LLM - Gemini Client

Google Gemini API 클라이언트

LEVEL 2:
- Gemini Pro, Gemini 1.5 지원
- GOOGLE_API_KEY 환경변수 필요
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
ALLOWED_GEMINI_MODELS = [
    "gemini-pro",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-2.0-flash-exp",
]


class GeminiClient(LLMClient):
    """
    Google Gemini Client
    
    GOOGLE_API_KEY 환경변수 필요
    """
    
    def __init__(self):
        self._client = None
        self._api_key = os.getenv("GOOGLE_API_KEY", "")
    
    @property
    def provider(self) -> str:
        return LLMProvider.GEMINI.value
    
    @property
    def client(self):
        """Gemini Client (Lazy initialization)"""
        if self._client is None:
            if not self._api_key:
                raise LLMClientError(
                    "GOOGLE_API_KEY not set",
                    provider=self.provider,
                    recoverable=False,
                )
            
            try:
                import google.generativeai as genai
                genai.configure(api_key=self._api_key)
                self._client = genai
            except ImportError:
                raise LLMClientError(
                    "google-generativeai package not installed. Run: pip install google-generativeai",
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
        """Gemini 응답 생성"""
        
        # 모델 검증
        if model not in ALLOWED_GEMINI_MODELS:
            raise LLMClientError(
                f"Model '{model}' not allowed. Allowed: {ALLOWED_GEMINI_MODELS}",
                provider=self.provider,
                model=model,
                recoverable=False,
            )
        
        start_time = time.time()
        
        try:
            # 모델 인스턴스 생성
            genai_model = self.client.GenerativeModel(model)
            
            # 메시지 변환
            prompt_parts = []
            for msg in messages:
                if msg.role == "system":
                    prompt_parts.append(f"[System Instructions]\n{msg.content}\n")
                elif msg.role == "user":
                    prompt_parts.append(f"[User]\n{msg.content}\n")
                elif msg.role == "assistant":
                    prompt_parts.append(f"[Assistant]\n{msg.content}\n")
            
            prompt = "\n".join(prompt_parts)
            
            # 생성 설정
            generation_config = self.client.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            
            # API 호출
            response = genai_model.generate_content(
                prompt,
                generation_config=generation_config,
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # 응답 파싱
            content = response.text if response.text else ""
            
            # 토큰 추정 (Gemini는 정확한 토큰 수를 제공하지 않을 수 있음)
            tokens_input = len(prompt) // 4  # 대략적 추정
            tokens_output = len(content) // 4
            
            logger.info(
                f"[GeminiClient] {model} | "
                f"tokens: ~{tokens_input}+{tokens_output}={tokens_input+tokens_output} | "
                f"latency: {latency_ms}ms"
            )
            
            return LLMResponse(
                content=content,
                model=model,
                provider=self.provider,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                latency_ms=latency_ms,
                finish_reason="stop",
            )
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            
            recoverable = "rate" in error_msg.lower() or "quota" in error_msg.lower()
            
            logger.error(f"[GeminiClient] Error: {error_msg}")
            
            raise LLMClientError(
                error_msg,
                provider=self.provider,
                model=model,
                recoverable=recoverable,
                original_error=e,
            )
