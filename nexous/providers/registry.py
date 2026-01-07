"""
NEXOUS Provider Registry

LLM Provider 등록 및 팩토리
"""

from __future__ import annotations

from typing import Dict, Type, Any

from .openai_provider import OpenAIProvider, LLMResponse
from .claude_provider import ClaudeProvider
from .gemini_provider import GeminiProvider


class ProviderRegistry:
    """LLM Provider 레지스트리"""
    
    PROVIDERS: Dict[str, Type] = {
        "openai": OpenAIProvider,
        "claude": ClaudeProvider,
        "anthropic": ClaudeProvider,  # alias
        "gemini": GeminiProvider,
        "google": GeminiProvider,  # alias
    }
    
    @classmethod
    def get(cls, provider: str, model: str = None, **kwargs) -> Any:
        """
        Provider 인스턴스 생성
        
        Args:
            provider: provider 이름 (openai, claude, gemini)
            model: 모델명 (옵션)
            **kwargs: 추가 설정
            
        Returns:
            Provider 인스턴스
        """
        provider_lower = provider.lower()
        
        if provider_lower not in cls.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}. Available: {list(cls.PROVIDERS.keys())}")
        
        provider_class = cls.PROVIDERS[provider_lower]
        return provider_class(model=model, **kwargs)
    
    @classmethod
    def list_providers(cls) -> list:
        """사용 가능한 provider 목록"""
        return list(set(cls.PROVIDERS.values()))
    
    @classmethod
    def is_available(cls, provider: str) -> bool:
        """provider 사용 가능 여부"""
        return provider.lower() in cls.PROVIDERS
