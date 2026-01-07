"""
NEXOUS LLM - Base Interface

LLM Client 인터페이스 및 타입 정의

LEVEL 2:
- OpenAI / Anthropic / Gemini 지원
- LLMPolicy 정의 (primary/retry/fallback)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class LLMProvider(str, Enum):
    """지원 Provider"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


@dataclass
class LLMMessage:
    """LLM 메시지"""
    role: str  # system, user, assistant
    content: str


@dataclass
class LLMResponse:
    """LLM 응답"""
    content: str
    model: str
    provider: str
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: int = 0
    finish_reason: str = "stop"
    
    # 폴백 정보
    attempt: int = 1
    fallback_from: Optional[str] = None
    
    @property
    def tokens_total(self) -> int:
        return self.tokens_input + self.tokens_output


@dataclass
class LLMPolicy:
    """
    LLM 선택 정책
    
    Preset에서 정의되며 Router가 이를 해석한다.
    """
    primary: str  # "openai/gpt-4o"
    retry: int = 3
    retry_delay: float = 1.0
    fallback: List[str] = field(default_factory=list)  # ["anthropic/claude-3-5-sonnet", "gemini/gemini-pro"]
    timeout: int = 60
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMPolicy":
        """딕셔너리에서 생성"""
        return cls(
            primary=data.get("primary", "openai/gpt-4o"),
            retry=data.get("retry", 3),
            retry_delay=data.get("retry_delay", 1.0),
            fallback=data.get("fallback", []),
            timeout=data.get("timeout", 60),
        )
    
    def get_provider_model(self, spec: str) -> tuple:
        """'provider/model' 파싱"""
        if "/" in spec:
            provider, model = spec.split("/", 1)
            return provider, model
        return spec, None


class LLMClient(ABC):
    """
    LLM Client 인터페이스
    
    모든 Provider Client는 이 인터페이스를 구현해야 한다.
    """
    
    @property
    @abstractmethod
    def provider(self) -> str:
        """Provider 이름"""
        pass
    
    @abstractmethod
    def generate(
        self,
        messages: List[LLMMessage],
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: int = 60,
        **kwargs
    ) -> LLMResponse:
        """
        LLM 응답 생성
        
        Args:
            messages: 메시지 리스트
            model: 모델명
            temperature: 온도
            max_tokens: 최대 토큰
            timeout: 타임아웃 (초)
            
        Returns:
            LLMResponse
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Client 사용 가능 여부 (API 키 등)"""
        pass


class LLMError(Exception):
    """LLM 기본 오류"""
    pass


class LLMClientError(LLMError):
    """LLM Client 오류"""
    
    def __init__(
        self,
        message: str,
        provider: str = "",
        model: str = "",
        recoverable: bool = True,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.recoverable = recoverable
        self.original_error = original_error


class LLMPolicyError(LLMError):
    """LLM Policy 관련 오류"""
    pass


class LLMAllProvidersFailedError(LLMError):
    """모든 Provider 실패"""
    
    def __init__(self, message: str, attempts: List[Dict[str, Any]]):
        super().__init__(message)
        self.attempts = attempts
