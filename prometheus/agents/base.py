"""
BaseAgent - 모든 Agent의 기반 추상 클래스

이 파일의 책임:
- Agent 공통 인터페이스 정의
- LLM 바인딩
- Tool 바인딩
- Memory 바인딩
- 실행 흐름 관리
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field

from prometheus.llm.base import BaseLLMClient, Message, MessageRole, LLMResponse


class AgentState(str, Enum):
    """Agent 상태"""
    
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentInput(BaseModel):
    """Agent 입력"""
    
    task: str
    context: Dict[str, Any] = Field(default_factory=dict)
    messages: List[Message] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @classmethod
    def from_text(cls, text: str, **kwargs) -> "AgentInput":
        """텍스트로부터 생성"""
        return cls(task=text, **kwargs)


class AgentOutput(BaseModel):
    """Agent 출력"""
    
    result: Any
    success: bool = True
    error: Optional[str] = None
    messages: List[Message] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    execution_time: float = 0.0
    token_usage: Dict[str, int] = Field(default_factory=dict)
    
    @classmethod
    def success_output(cls, result: Any, **kwargs) -> "AgentOutput":
        """성공 출력 생성"""
        return cls(result=result, success=True, **kwargs)
    
    @classmethod
    def error_output(cls, error: str, **kwargs) -> "AgentOutput":
        """실패 출력 생성"""
        return cls(result=None, success=False, error=error, **kwargs)


class AgentConfig(BaseModel):
    """Agent 설정"""
    
    name: str = "BaseAgent"
    system_prompt: Optional[str] = None
    max_iterations: int = 10
    temperature: Optional[float] = None
    timeout: float = 300.0
    retry_count: int = 3
    verbose: bool = False


class BaseAgent(ABC):
    """
    모든 Agent의 기반 추상 클래스
    
    PROMETHEUS의 모든 Agent가 상속하는 기반 클래스입니다.
    LLM, Tool, Memory 바인딩 및 실행 흐름을 관리합니다.
    """
    
    agent_type: str = "base"
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        llm: Optional[BaseLLMClient] = None,
        tools: Optional[List[Any]] = None,
        memory: Optional[Any] = None,
    ) -> None:
        """
        BaseAgent 초기화
        
        Args:
            config: Agent 설정
            llm: LLM 클라이언트
            tools: Tool 목록
            memory: Memory 인스턴스
        """
        self.config = config or AgentConfig()
        self._llm = llm
        self._tools: Dict[str, Any] = {}
        self._memory = memory
        self._state = AgentState.IDLE
        self._messages: List[Message] = []
        self._iteration_count = 0
        self._start_time: Optional[datetime] = None
        
        # Tools 등록
        if tools:
            for tool in tools:
                self.bind_tool(tool)
    
    @abstractmethod
    async def run(
        self,
        input: AgentInput,
    ) -> AgentOutput:
        """
        Agent 실행
        
        Args:
            input: Agent 입력
            
        Returns:
            Agent 출력
        """
        pass
    
    async def stream(
        self,
        input: AgentInput,
    ) -> AsyncIterator[str]:
        """
        스트리밍 실행
        
        Args:
            input: Agent 입력
            
        Yields:
            스트리밍 출력
        """
        # 기본 구현: 일반 실행 후 결과 반환
        output = await self.run(input)
        yield str(output.result)
    
    def bind_llm(
        self,
        llm: BaseLLMClient,
    ) -> "BaseAgent":
        """
        LLM 바인딩
        
        Args:
            llm: LLM 클라이언트
            
        Returns:
            self (체이닝 지원)
        """
        self._llm = llm
        return self
    
    def bind_tool(
        self,
        tool: Any,
    ) -> "BaseAgent":
        """
        Tool 바인딩
        
        Args:
            tool: Tool 인스턴스
            
        Returns:
            self (체이닝 지원)
        """
        tool_name = getattr(tool, 'name', str(tool.__class__.__name__))
        self._tools[tool_name] = tool
        return self
    
    def bind_tools(
        self,
        tools: List[Any],
    ) -> "BaseAgent":
        """
        여러 Tool 바인딩
        
        Args:
            tools: Tool 목록
            
        Returns:
            self (체이닝 지원)
        """
        for tool in tools:
            self.bind_tool(tool)
        return self
    
    def bind_memory(
        self,
        memory: Any,
    ) -> "BaseAgent":
        """
        Memory 바인딩
        
        Args:
            memory: Memory 인스턴스
            
        Returns:
            self (체이닝 지원)
        """
        self._memory = memory
        return self
    
    def unbind_tool(
        self,
        tool_name: str,
    ) -> bool:
        """
        Tool 바인딩 해제
        
        Args:
            tool_name: Tool 이름
            
        Returns:
            해제 성공 여부
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            return True
        return False
    
    @property
    def llm(self) -> Optional[BaseLLMClient]:
        """바인딩된 LLM"""
        return self._llm
    
    @property
    def tools(self) -> Dict[str, Any]:
        """바인딩된 Tools"""
        return self._tools
    
    @property
    def memory(self) -> Optional[Any]:
        """바인딩된 Memory"""
        return self._memory
    
    @property
    def state(self) -> AgentState:
        """현재 상태"""
        return self._state
    
    @property
    def messages(self) -> List[Message]:
        """대화 히스토리"""
        return self._messages
    
    def get_system_prompt(self) -> str:
        """
        시스템 프롬프트 조회
        
        Returns:
            시스템 프롬프트 문자열
        """
        return self.config.system_prompt or self._default_system_prompt()
    
    def _default_system_prompt(self) -> str:
        """
        기본 시스템 프롬프트
        
        Returns:
            기본 프롬프트
        """
        return f"You are a helpful AI assistant. Agent type: {self.agent_type}"
    
    async def _call_llm(
        self,
        messages: List[Message],
        **kwargs: Any,
    ) -> LLMResponse:
        """
        LLM 호출
        
        Args:
            messages: 메시지 목록
            **kwargs: 추가 옵션
            
        Returns:
            LLM 응답
        """
        if self._llm is None:
            raise ValueError("LLM is not bound to this agent")
        
        # temperature 오버라이드
        if self.config.temperature is not None and "temperature" not in kwargs:
            kwargs["temperature"] = self.config.temperature
        
        return await self._llm.generate(messages, **kwargs)
    
    async def _call_llm_with_tools(
        self,
        messages: List[Message],
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Tool과 함께 LLM 호출
        
        Args:
            messages: 메시지 목록
            **kwargs: 추가 옵션
            
        Returns:
            LLM 응답
        """
        if self._llm is None:
            raise ValueError("LLM is not bound to this agent")
        
        # Tool 스키마 생성
        tool_schemas = self._get_tool_schemas()
        
        if tool_schemas:
            return await self._llm.generate_with_tools(
                messages,
                tools=tool_schemas,
                **kwargs
            )
        else:
            return await self._call_llm(messages, **kwargs)
    
    def _get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Tool 스키마 목록 생성
        
        Returns:
            Tool 스키마 목록
        """
        schemas = []
        for name, tool in self._tools.items():
            if hasattr(tool, 'get_schema'):
                schema = tool.get_schema()
                schemas.append({
                    "name": schema.name,
                    "description": schema.description,
                    "parameters": self._schema_to_parameters(schema),
                })
            elif hasattr(tool, 'to_openai_function'):
                schemas.append(tool.to_openai_function())
            else:
                # 기본 스키마
                schemas.append({
                    "name": name,
                    "description": getattr(tool, 'description', f"Tool: {name}"),
                    "parameters": {"type": "object", "properties": {}},
                })
        return schemas
    
    def _schema_to_parameters(self, schema: Any) -> Dict[str, Any]:
        """
        ToolSchema를 OpenAI parameters 형식으로 변환
        
        Args:
            schema: ToolSchema
            
        Returns:
            parameters 딕셔너리
        """
        properties = {}
        required = []
        
        if hasattr(schema, 'parameters'):
            for param in schema.parameters:
                properties[param.name] = {
                    "type": param.type,
                    "description": param.description,
                }
                if param.required:
                    required.append(param.name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }
    
    async def _execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Any:
        """
        Tool 실행
        
        Args:
            tool_name: Tool 이름
            arguments: 인자
            
        Returns:
            실행 결과
        """
        tool = self._tools.get(tool_name)
        if tool is None:
            raise ValueError(f"Tool not found: {tool_name}")
        
        if hasattr(tool, 'execute'):
            return await tool.execute(**arguments)
        elif callable(tool):
            return await tool(**arguments) if asyncio.iscoroutinefunction(tool) else tool(**arguments)
        else:
            raise ValueError(f"Tool {tool_name} is not executable")
    
    def _set_state(self, state: AgentState) -> None:
        """상태 설정"""
        self._state = state
    
    def _add_message(self, message: Message) -> None:
        """메시지 추가"""
        self._messages.append(message)
    
    def _clear_messages(self) -> None:
        """메시지 초기화"""
        self._messages.clear()
    
    def reset(self) -> None:
        """Agent 상태 초기화"""
        self._state = AgentState.IDLE
        self._messages.clear()
        self._iteration_count = 0
        self._start_time = None
    
    def get_info(self) -> Dict[str, Any]:
        """
        Agent 정보 조회
        
        Returns:
            Agent 정보 딕셔너리
        """
        return {
            "agent_type": self.agent_type,
            "name": self.config.name,
            "state": self._state.value,
            "llm_bound": self._llm is not None,
            "tools_count": len(self._tools),
            "memory_bound": self._memory is not None,
            "message_count": len(self._messages),
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.config.name}, state={self._state.value})"


# asyncio import (for _execute_tool)
import asyncio
