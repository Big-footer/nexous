"""
BaseTool - 모든 Tool의 기반 추상 클래스

이 파일의 책임:
- Tool 공통 인터페이스 정의
- Tool 스키마 정의
- 실행 결과 형식 표준화
- Tool 등록 및 관리
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class ToolParameterType(str, Enum):
    """Tool 파라미터 타입"""
    
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class ToolParameter(BaseModel):
    """Tool 파라미터 정의"""
    
    name: str
    type: ToolParameterType = ToolParameterType.STRING
    description: str = ""
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    
    def to_json_schema(self) -> Dict[str, Any]:
        """JSON Schema 형식으로 변환"""
        schema = {
            "type": self.type.value,
            "description": self.description,
        }
        if self.enum:
            schema["enum"] = self.enum
        if self.default is not None:
            schema["default"] = self.default
        return schema


class ToolSchema(BaseModel):
    """Tool 스키마"""
    
    name: str
    description: str
    parameters: List[ToolParameter] = Field(default_factory=list)
    returns: str = "Any"
    examples: List[Dict[str, Any]] = Field(default_factory=list)
    
    def to_openai_function(self) -> Dict[str, Any]:
        """OpenAI Function 형식으로 변환"""
        properties = {}
        required = []
        
        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }
    
    def to_anthropic_tool(self) -> Dict[str, Any]:
        """Anthropic Tool 형식으로 변환"""
        properties = {}
        required = []
        
        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)
        
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }


class ToolResult(BaseModel):
    """Tool 실행 결과"""
    
    success: bool = True
    output: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    @classmethod
    def success_result(cls, output: Any, **kwargs) -> "ToolResult":
        """성공 결과 생성"""
        return cls(success=True, output=output, **kwargs)
    
    @classmethod
    def error_result(cls, error: str, **kwargs) -> "ToolResult":
        """실패 결과 생성"""
        return cls(success=False, error=error, **kwargs)
    
    def to_string(self) -> str:
        """문자열로 변환 (LLM 응답용)"""
        if self.success:
            if isinstance(self.output, str):
                return self.output
            return str(self.output)
        else:
            return f"Error: {self.error}"


class ToolConfig(BaseModel):
    """Tool 설정"""
    
    enabled: bool = True
    timeout: float = 60.0
    max_retries: int = 3
    retry_delay: float = 1.0
    config: Dict[str, Any] = Field(default_factory=dict)


class BaseTool(ABC):
    """
    모든 Tool의 기반 추상 클래스
    
    PROMETHEUS의 모든 Tool이 상속하는 기반 클래스입니다.
    Tool 스키마, 실행, 검증 등의 공통 인터페이스를 제공합니다.
    """
    
    # 서브클래스에서 오버라이드
    name: str = "base_tool"
    description: str = "Base tool description"
    
    def __init__(
        self,
        config: Optional[ToolConfig] = None,
    ) -> None:
        """
        BaseTool 초기화
        
        Args:
            config: Tool 설정
        """
        self.config = config or ToolConfig()
        self._execution_count = 0
        self._total_execution_time = 0.0
    
    @abstractmethod
    async def execute(
        self,
        **kwargs: Any,
    ) -> ToolResult:
        """
        Tool 실행
        
        Args:
            **kwargs: Tool 파라미터
            
        Returns:
            실행 결과
        """
        pass
    
    @abstractmethod
    def get_schema(self) -> ToolSchema:
        """
        Tool 스키마 조회
        
        Returns:
            Tool 스키마
        """
        pass
    
    def validate_params(
        self,
        **kwargs: Any,
    ) -> List[str]:
        """
        파라미터 검증
        
        Args:
            **kwargs: 검증할 파라미터
            
        Returns:
            오류 메시지 목록 (빈 목록이면 유효)
        """
        errors = []
        schema = self.get_schema()
        
        for param in schema.parameters:
            if param.required and param.name not in kwargs:
                errors.append(f"Missing required parameter: {param.name}")
            
            if param.name in kwargs:
                value = kwargs[param.name]
                # 타입 검증 (기본적인 검증만)
                if param.type == ToolParameterType.STRING and not isinstance(value, str):
                    errors.append(f"Parameter {param.name} must be string")
                elif param.type == ToolParameterType.INTEGER and not isinstance(value, int):
                    errors.append(f"Parameter {param.name} must be integer")
                elif param.type == ToolParameterType.BOOLEAN and not isinstance(value, bool):
                    errors.append(f"Parameter {param.name} must be boolean")
                
                # enum 검증
                if param.enum and value not in param.enum:
                    errors.append(f"Parameter {param.name} must be one of: {param.enum}")
        
        return errors
    
    async def safe_execute(
        self,
        **kwargs: Any,
    ) -> ToolResult:
        """
        안전한 실행 (검증 + 예외 처리)
        
        Args:
            **kwargs: Tool 파라미터
            
        Returns:
            실행 결과
        """
        import time
        
        # 파라미터 검증
        errors = self.validate_params(**kwargs)
        if errors:
            return ToolResult.error_result("; ".join(errors))
        
        # 실행
        start_time = time.time()
        try:
            result = await self.execute(**kwargs)
            execution_time = time.time() - start_time
            
            result.execution_time = execution_time
            self._execution_count += 1
            self._total_execution_time += execution_time
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            return ToolResult.error_result(
                error=str(e),
                execution_time=execution_time,
            )
    
    def to_openai_function(self) -> Dict[str, Any]:
        """OpenAI Function 형식으로 변환"""
        return self.get_schema().to_openai_function()
    
    def to_anthropic_tool(self) -> Dict[str, Any]:
        """Anthropic Tool 형식으로 변환"""
        return self.get_schema().to_anthropic_tool()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        실행 통계 조회
        
        Returns:
            통계 딕셔너리
        """
        return {
            "name": self.name,
            "execution_count": self._execution_count,
            "total_execution_time": self._total_execution_time,
            "avg_execution_time": (
                self._total_execution_time / self._execution_count
                if self._execution_count > 0 else 0
            ),
            "enabled": self.config.enabled,
        }
    
    def reset_stats(self) -> None:
        """통계 초기화"""
        self._execution_count = 0
        self._total_execution_time = 0.0
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, enabled={self.config.enabled})"


class ToolRegistry:
    """
    Tool 레지스트리
    
    Tool을 등록하고 관리합니다.
    """
    
    def __init__(self) -> None:
        """ToolRegistry 초기화"""
        self._tools: Dict[str, BaseTool] = {}
    
    def register(
        self,
        tool: BaseTool,
    ) -> None:
        """
        Tool 등록
        
        Args:
            tool: Tool 인스턴스
        """
        self._tools[tool.name] = tool
    
    def unregister(
        self,
        name: str,
    ) -> bool:
        """
        Tool 등록 해제
        
        Args:
            name: Tool 이름
            
        Returns:
            해제 성공 여부
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False
    
    def get(
        self,
        name: str,
    ) -> Optional[BaseTool]:
        """
        Tool 조회
        
        Args:
            name: Tool 이름
            
        Returns:
            Tool 또는 None
        """
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """등록된 Tool 이름 목록"""
        return list(self._tools.keys())
    
    def get_all_schemas(self) -> List[ToolSchema]:
        """모든 Tool 스키마 목록"""
        return [tool.get_schema() for tool in self._tools.values()]
    
    def get_enabled_tools(self) -> List[BaseTool]:
        """활성화된 Tool 목록"""
        return [
            tool for tool in self._tools.values()
            if tool.config.enabled
        ]
    
    async def execute(
        self,
        name: str,
        **kwargs: Any,
    ) -> ToolResult:
        """
        Tool 실행
        
        Args:
            name: Tool 이름
            **kwargs: 파라미터
            
        Returns:
            실행 결과
        """
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult.error_result(f"Tool not found: {name}")
        
        if not tool.config.enabled:
            return ToolResult.error_result(f"Tool is disabled: {name}")
        
        return await tool.safe_execute(**kwargs)


# 전역 레지스트리
_default_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """기본 ToolRegistry 인스턴스 획득"""
    global _default_registry
    if _default_registry is None:
        _default_registry = ToolRegistry()
    return _default_registry
