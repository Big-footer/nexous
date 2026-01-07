"""
NEXOUS Provider - Claude (Anthropic)

Claude LLM Provider 구현
"""

from __future__ import annotations

import os
import time
import logging
from typing import Dict, Any, List, Optional

from .openai_provider import LLMResponse

logger = logging.getLogger(__name__)


class ClaudeProvider:
    """
    Claude LLM Provider (Anthropic)
    
    LEVEL 2: 에이전트 능력 확장
    - claude-sonnet-4-20250514 기본
    - retry / timeout / token logging
    """
    
    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    MAX_RETRIES = 3
    TIMEOUT = 120  # seconds
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model or self.DEFAULT_MODEL
        self._client = None
        
        if not self.api_key:
            logger.warning("[Claude] API key not found. Set ANTHROPIC_API_KEY environment variable.")
    
    @property
    def client(self):
        """Lazy initialization of Anthropic client"""
        if self._client is None:
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
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
        # Retry 로직
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                start_time = time.time()
                
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_prompt or "",
                    messages=messages,
                    temperature=temperature
                )
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                # 토큰 사용량
                usage = response.usage
                tokens_input = usage.input_tokens if usage else 0
                tokens_output = usage.output_tokens if usage else 0
                tokens_total = tokens_input + tokens_output
                
                # 응답 내용
                content = response.content[0].text if response.content else ""
                
                logger.info(
                    f"[Claude] {self.model} | "
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
                    provider="claude"
                )
                
            except Exception as e:
                last_error = e
                logger.warning(f"[Claude] Attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        raise RuntimeError(f"Claude API failed after {self.MAX_RETRIES} retries: {last_error}")
