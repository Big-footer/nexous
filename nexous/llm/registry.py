"""
NEXOUS LLM - Registry

Provider -> LLMClient 매핑

LEVEL 2:
- OpenAI / Anthropic / Gemini 지원
- Provider별 싱글톤 캐시
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from .base import LLMClient, LLMClientError, LLMProvider

logger = logging.getLogger(__name__)


class LLMRegistry:
    """
    LLM Client Registry
    
    Provider 이름으로 LLMClient 인스턴스를 반환한다.
    """
    
    _instances: Dict[str, LLMClient] = {}
    
    @classmethod
    def get(cls, provider: str) -> LLMClient:
        """
        Provider에 해당하는 LLMClient 반환
        
        Args:
            provider: "openai", "anthropic", "gemini"
            
        Returns:
            LLMClient 인스턴스
        """
        provider = provider.lower()
        
        # 캐시된 인스턴스
        if provider in cls._instances:
            return cls._instances[provider]
        
        # 새 인스턴스 생성
        client = cls._create_client(provider)
        cls._instances[provider] = client
        
        logger.info(f"[LLMRegistry] Created {provider} client")
        return client
    
    @classmethod
    def _create_client(cls, provider: str) -> LLMClient:
        """Provider별 Client 생성"""
        
        if provider == LLMProvider.OPENAI.value:
            from .openai_client import OpenAIClient
            return OpenAIClient()
        
        elif provider == LLMProvider.ANTHROPIC.value:
            from .anthropic_client import AnthropicClient
            return AnthropicClient()
        
        elif provider == LLMProvider.GEMINI.value:
            from .gemini_client import GeminiClient
            return GeminiClient()
        
        else:
            raise LLMClientError(
                f"Unknown provider: {provider}. "
                f"Supported: {cls.list_providers()}",
                provider=provider,
                recoverable=False,
            )
    
    @classmethod
    def list_providers(cls) -> List[str]:
        """지원 Provider 목록"""
        return [p.value for p in LLMProvider]
    
    @classmethod
    def is_available(cls, provider: str) -> bool:
        """Provider 사용 가능 여부"""
        try:
            client = cls.get(provider)
            return client.is_available()
        except LLMClientError:
            return False
    
    @classmethod
    def clear_cache(cls) -> None:
        """캐시 초기화"""
        cls._instances.clear()


def get_llm_registry() -> type:
    """Registry 클래스 반환"""
    return LLMRegistry
