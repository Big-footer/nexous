"""
NEXOUS Provider - Gemini (Google)

Gemini LLM Provider 구현
"""

from __future__ import annotations

import os
import time
import logging
from typing import Dict, Any, List, Optional

from .openai_provider import LLMResponse

logger = logging.getLogger(__name__)


class GeminiProvider:
    """
    Gemini LLM Provider (Google)
    
    LEVEL 2: 에이전트 능력 확장
    - gemini-2.0-flash 기본
    - retry / timeout / token logging
    """
    
    DEFAULT_MODEL = "gemini-2.0-flash"
    MAX_RETRIES = 3
    TIMEOUT = 120  # seconds
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.model = model or self.DEFAULT_MODEL
        self._client = None
        
        if not self.api_key:
            logger.warning("[Gemini] API key not found. Set GOOGLE_API_KEY environment variable.")
    
    @property
    def client(self):
        """Lazy initialization of Gemini client"""
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel(self.model)
            except ImportError:
                raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")
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
        """
        # Gemini 형식으로 변환
        prompt_parts = []
        
        if system_prompt:
            prompt_parts.append(f"System: {system_prompt}\n\n")
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        full_prompt = "\n".join(prompt_parts)
        
        # Retry 로직
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                start_time = time.time()
                
                response = self.client.generate_content(
                    full_prompt,
                    generation_config={
                        "temperature": temperature,
                        "max_output_tokens": max_tokens,
                    }
                )
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                # 토큰 추정 (Gemini는 정확한 토큰 수 제공하지 않음)
                content = response.text if response.text else ""
                tokens_input = len(full_prompt) // 4  # 대략적 추정
                tokens_output = len(content) // 4
                tokens_total = tokens_input + tokens_output
                
                logger.info(
                    f"[Gemini] {self.model} | "
                    f"tokens: ~{tokens_input}+{tokens_output}={tokens_total} | "
                    f"latency: {latency_ms}ms"
                )
                
                return LLMResponse(
                    content=content,
                    tokens_input=tokens_input,
                    tokens_output=tokens_output,
                    tokens_total=tokens_total,
                    latency_ms=latency_ms,
                    model=self.model,
                    provider="gemini"
                )
                
            except Exception as e:
                last_error = e
                logger.warning(f"[Gemini] Attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
        
        raise RuntimeError(f"Gemini API failed after {self.MAX_RETRIES} retries: {last_error}")
