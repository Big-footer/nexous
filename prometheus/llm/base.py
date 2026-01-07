"""
BaseLLMClient - 모든 LLM 클라이언트의 기반 추상 클래스

이 파일의 책임:
- 모든 LLM 클라이언트 공통 인터페이스 정의
- 메시지 형식 표준화
- 응답 형식 표준화
- 토큰 카운팅 인터페이스
- 스트리밍 인터페이스
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class MessageRole(str, Enum):
    """메시지 역할"""
    
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


class Message(BaseModel):
    """대화 메시지"""
    
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    
    @classmethod
    def system(cls, content: str) -> "Message":
        """시스템 메시지 생성"""
        return cls(role=MessageRole.SYSTEM, content=content)
    
    @classmethod
    def user(cls, content: str) -> "Message":
        """사용자 메시지 생성"""
        return cls(role=MessageRole.USER, content=content)
    
    @classmethod
    def assistant(cls, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None) -> "Message":
        """어시스턴트 메시지 생성"""
        return cls(role=MessageRole.ASSISTANT, content=content, tool_calls=tool_calls)
    
    @classmethod
    def tool(cls, content: str, tool_call_id: str) -> "Message":
        """Tool 결과 메시지 생성"""
        return cls(role=MessageRole.TOOL, content=content, tool_call_id=tool_call_id)


class TokenUsage(BaseModel):
    """토큰 사용량"""
    
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        """토큰 사용량 합산"""
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


class LLMResponse(BaseModel):
    """LLM 응답"""
    
    content: str
    role: MessageRole = MessageRole.ASSISTANT
    model: str = ""
    usage: TokenUsage = Field(default_factory=TokenUsage)
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    
    def has_tool_calls(self) -> bool:
        """Tool 호출 여부"""
        return self.tool_calls is not None and len(self.tool_calls) > 0
    
    def to_message(self) -> Message:
        """응답을 Message로 변환"""
        return Message(
            role=self.role,
            content=self.content,
            tool_calls=self.tool_calls,
        )


class LLMConfig(BaseModel):
    """LLM 설정"""
    
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    timeout: float = 60.0
    stop: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """API 호출용 딕셔너리로 변환"""
        result = {
            "model": self.model,
            "temperature": self.temperature,
            "top_p": self.top_p,
        }
        if self.max_tokens:
            result["max_tokens"] = self.max_tokens
        if self.frequency_penalty != 0:
            result["frequency_penalty"] = self.frequency_penalty
        if self.presence_penalty != 0:
            result["presence_penalty"] = self.presence_penalty
        if self.stop:
            result["stop"] = self.stop
        return result


class LLMError(Exception):
    """LLM 관련 오류"""
    
    def __init__(self, message: str, provider: str = "", original_error: Optional[Exception] = None):
        super().__init__(message)
        self.provider = provider
        self.original_error = original_error


class RateLimitError(LLMError):
    """Rate Limit 오류"""
    pass


class AuthenticationError(LLMError):
    """인증 오류"""
    pass


class BaseLLMClient(ABC):
    """
    모든 LLM 클라이언트의 기반 추상 클래스
    
    OpenAI, Anthropic, Gemini 등 다양한 LLM 프로바이더를
    동일한 인터페이스로 사용할 수 있도록 추상화합니다.
    """
    
    provider: str = "base"
    
    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        api_key: Optional[str] = None,
    ) -> None:
        """
        BaseLLMClient 초기화
        
        Args:
            config: LLM 설정
            api_key: API 키
        """
        self.config = config or LLMConfig(model="default")
        self.api_key = api_key
        self._is_connected = False
        self._total_usage = TokenUsage()
    
    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        **kwargs: Any,
    ) -> LLMResponse:
        """
        텍스트 생성
        
        Args:
            messages: 대화 메시지 목록
            **kwargs: 추가 옵션 (temperature, max_tokens 등)
            
        Returns:
            LLM 응답
        """
        pass
    
    @abstractmethod
    async def stream(
        self,
        messages: List[Message],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        스트리밍 생성
        
        Args:
            messages: 대화 메시지 목록
            **kwargs: 추가 옵션
            
        Yields:
            스트리밍 응답 청크
        """
        pass
    
    @abstractmethod
    def count_tokens(
        self,
        text: str,
    ) -> int:
        """
        토큰 수 계산
        
        Args:
            text: 텍스트
            
        Returns:
            토큰 수
        """
        pass
    
    async def generate_with_tools(
        self,
        messages: List[Message],
        tools: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Tool 사용 가능한 생성
        
        Args:
            messages: 대화 메시지 목록
            tools: Tool 정의 목록
            **kwargs: 추가 옵션
            
        Returns:
            LLM 응답 (tool_calls 포함 가능)
        """
        # 기본 구현 - 서브클래스에서 오버라이드
        return await self.generate(messages, tools=tools, **kwargs)
    
    async def chat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """
        간편한 채팅 인터페이스
        
        Args:
            user_message: 사용자 메시지
            system_prompt: 시스템 프롬프트
            **kwargs: 추가 옵션
            
        Returns:
            응답 텍스트
        """
        messages = []
        if system_prompt:
            messages.append(Message.system(system_prompt))
        messages.append(Message.user(user_message))
        
        response = await self.generate(messages, **kwargs)
        return response.content
    
    def validate_api_key(self) -> bool:
        """
        API 키 유효성 확인
        
        Returns:
            유효 여부
        """
        return self.api_key is not None and len(self.api_key) > 0
    
    @property
    def is_connected(self) -> bool:
        """연결 상태"""
        return self._is_connected
    
    @property
    def total_usage(self) -> TokenUsage:
        """총 토큰 사용량"""
        return self._total_usage
    
    def reset_usage(self) -> None:
        """토큰 사용량 초기화"""
        self._total_usage = TokenUsage()
    
    def _update_usage(self, usage: TokenUsage) -> None:
        """토큰 사용량 업데이트"""
        self._total_usage = self._total_usage + usage
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        모델 정보 조회
        
        Returns:
            모델 정보 딕셔너리
        """
        return {
            "provider": self.provider,
            "model": self.config.model,
            "is_connected": self._is_connected,
            "total_usage": self._total_usage.model_dump(),
        }
    
    def _merge_config(self, **kwargs: Any) -> Dict[str, Any]:
        """
        기본 설정과 kwargs 병합
        
        Args:
            **kwargs: 오버라이드할 설정
            
        Returns:
            병합된 설정
        """
        base = self.config.to_dict()
        for key, value in kwargs.items():
            if value is not None:
                base[key] = value
        return base
    
    @abstractmethod
    def _format_messages(
        self,
        messages: List[Message],
    ) -> Any:
        """
        메시지를 프로바이더 형식으로 변환
        
        Args:
            messages: 표준 메시지 목록
            
        Returns:
            프로바이더 형식 메시지
        """
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(provider={self.provider}, model={self.config.model})"
