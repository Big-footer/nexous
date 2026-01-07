"""
BaseTool - 모든 Tool의 기반 추상 클래스

이 파일의 책임:
- 모든 Tool이 공유하는 공통 인터페이스 정의
- Tool 메타데이터 (이름, 설명, 파라미터 스키마) 관리
- Tool 실행 인터페이스 정의
- 실행 결과 표준화
- LangChain Tool 호환 인터페이스
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """Tool 파라미터 정의"""
    
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None


class ToolSchema(BaseModel):
    """Tool 스키마 정의"""
    
    name: str
    description: str
    parameters: List[ToolParameter] = []
    returns: str = "string"


class ToolResult(BaseModel):
    """Tool 실행 결과"""
    
    success: bool
    output: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    execution_time: float = 0.0


class BaseTool(ABC):
    """
    모든 Tool의 기반 추상 클래스
    
    모든 Tool은 이 클래스를 상속받아 구현합니다.
    LangChain Tool과 호환되는 인터페이스를 제공합니다.
    """
    
    # 서브클래스에서 오버라이드할 속성
    name: str = "base_tool"
    description: str = "Base tool description"
    
    def __init__(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """
        BaseTool 초기화
        
        Args:
            name: Tool 이름 (지정 시 클래스 속성 오버라이드)
            description: Tool 설명 (지정 시 클래스 속성 오버라이드)
        """
        if name:
            self.name = name
        if description:
            self.description = description
        self._is_enabled = True
    
    @abstractmethod
    async def execute(
        self,
        **kwargs: Any,
    ) -> ToolResult:
        """
        Tool 실행
        
        Args:
            **kwargs: Tool 인자
            
        Returns:
            실행 결과
        """
        pass
    
    @abstractmethod
    def get_schema(self) -> ToolSchema:
        """
        Tool 스키마 반환
        
        Returns:
            Tool 스키마
        """
        pass
    
    def validate_input(
        self,
        **kwargs: Any,
    ) -> bool:
        """
        입력 검증
        
        Args:
            **kwargs: 검증할 입력
            
        Returns:
            검증 결과
        """
        # TODO: 입력 검증 로직
        pass
    
    def enable(self) -> None:
        """Tool 활성화"""
        self._is_enabled = True
    
    def disable(self) -> None:
        """Tool 비활성화"""
        self._is_enabled = False
    
    @property
    def is_enabled(self) -> bool:
        """활성화 여부"""
        return self._is_enabled
    
    def to_langchain_tool(self) -> Any:
        """
        LangChain Tool로 변환
        
        Returns:
            LangChain Tool 인스턴스
        """
        # TODO: LangChain Tool 변환 로직
        pass
    
    def to_openai_function(self) -> Dict[str, Any]:
        """
        OpenAI Function Calling 형식으로 변환
        
        Returns:
            OpenAI function 스키마
        """
        # TODO: OpenAI function 변환 로직
        pass
    
    def __repr__(self) -> str:
        """문자열 표현"""
        return f"{self.__class__.__name__}(name={self.name})"
