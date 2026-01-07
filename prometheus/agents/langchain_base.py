"""
PROMETHEUS LangChain BaseAgent (LCEL Refactored)

모든 Agent의 기반 클래스
LangChain의 최신 API(LCEL, Runnable)를 완전히 활용합니다.

주요 개선사항:
- Runnable 인터페이스 구현으로 LCEL 체인에 통합 가능
- with_fallbacks(), with_retry() 등 LCEL 기능 활용
- 타입 안전성 강화
- 스트리밍, 배치 처리 지원
"""

from abc import ABC, abstractmethod
from typing import (
    Any, Dict, List, Optional, Type, Union, 
    Iterator, AsyncIterator, TypeVar, Generic
)
from datetime import datetime
from enum import Enum
import logging

from pydantic import BaseModel, Field
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser, PydanticOutputParser
from langchain_core.runnables import (
    Runnable, 
    RunnableConfig,
    RunnablePassthrough, 
    RunnableLambda,
    RunnableParallel,
    RunnableSequence,
)
from langchain_core.runnables.utils import Input, Output

logger = logging.getLogger(__name__)


# =============================================================================
# Type Variables
# =============================================================================
InputType = TypeVar("InputType", bound=Union[str, Dict[str, Any]])
OutputType = TypeVar("OutputType")


# =============================================================================
# Enums & Config
# =============================================================================

class AgentRole(str, Enum):
    """Agent 역할"""
    META = "meta"
    PLANNER = "planner"
    EXECUTOR = "executor"
    WRITER = "writer"
    QA = "qa"


class AgentConfig(BaseModel):
    """Agent 설정"""
    name: str = Field(default="BaseAgent", description="Agent 이름")
    role: AgentRole = Field(default=AgentRole.META, description="Agent 역할")
    system_prompt: str = Field(default="", description="시스템 프롬프트")
    temperature: float = Field(default=0.7, description="LLM 온도")
    max_tokens: int = Field(default=2000, description="최대 토큰")
    retry_count: int = Field(default=3, description="재시도 횟수")
    timeout: float = Field(default=300.0, description="타임아웃(초)")
    
    model_config = {"use_enum_values": True}


class AgentOutput(BaseModel):
    """Agent 출력 기본 형식"""
    success: bool = Field(default=True, description="성공 여부")
    result: Any = Field(default=None, description="결과")
    error: Optional[str] = Field(default=None, description="에러 메시지")
    execution_time: float = Field(default=0.0, description="실행 시간(초)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="메타데이터")


# =============================================================================
# Base Agent (Runnable 구현)
# =============================================================================

class BaseLangChainAgent(Runnable[InputType, OutputType], ABC):
    """
    LangChain 기반 BaseAgent (Runnable 인터페이스 구현)
    
    모든 PROMETHEUS Agent가 상속하는 기반 클래스입니다.
    Runnable 인터페이스를 구현하여 LCEL 체인에 완전히 통합됩니다.
    
    LCEL 기능 지원:
    - invoke(), ainvoke(): 동기/비동기 실행
    - stream(), astream(): 스트리밍
    - batch(), abatch(): 배치 처리
    - with_fallbacks(): 실패 시 대체 실행
    - with_retry(): 재시도 로직
    - pipe (|): 체인 연결
    
    Example:
        ```python
        # Agent를 LCEL 체인에 연결
        chain = prompt | agent | parser
        
        # Fallback 설정
        agent_with_fallback = agent.with_fallbacks([backup_agent])
        
        # 재시도 설정
        agent_with_retry = agent.with_retry(stop_after_attempt=3)
        ```
    """
    
    role: AgentRole = AgentRole.META
    
    def __init__(
        self,
        llm: BaseChatModel,
        config: Optional[AgentConfig] = None,
        tools: Optional[List[Any]] = None,
        memory: Optional[Any] = None,
    ):
        """
        초기화
        
        Args:
            llm: LangChain LLM 인스턴스
            config: Agent 설정
            tools: 사용할 Tool 목록
            memory: Memory 인스턴스
        """
        self.llm = llm
        self.config = config or AgentConfig(role=self.role)
        self.tools = tools or []
        self.memory = memory
        
        # LCEL Chain 구성
        self.chain: Runnable = self._build_chain()
    
    @abstractmethod
    def _build_chain(self) -> Runnable:
        """
        LCEL Chain 구성 (하위 클래스에서 구현)
        
        Returns:
            Runnable: LCEL 체인
        """
        pass
    
    @abstractmethod
    def _get_system_prompt(self) -> str:
        """시스템 프롬프트 반환 (하위 클래스에서 구현)"""
        pass
    
    def _normalize_input(self, input_data: InputType) -> Dict[str, Any]:
        """입력 데이터 정규화"""
        if isinstance(input_data, str):
            return {"input": input_data}
        elif isinstance(input_data, dict):
            return input_data
        else:
            return {"input": str(input_data)}
    
    # =========================================================================
    # Runnable 인터페이스 구현
    # =========================================================================
    
    def invoke(
        self,
        input: InputType,
        config: Optional[RunnableConfig] = None,
        **kwargs,
    ) -> OutputType:
        """
        동기 실행 (Runnable 인터페이스)
        
        Args:
            input: 입력 데이터
            config: Runnable 설정
            **kwargs: 추가 인자
        
        Returns:
            출력 결과
        """
        start_time = datetime.now()
        input_dict = self._normalize_input(input)
        
        try:
            result = self.chain.invoke(input_dict, config=config, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.debug(f"{self.config.name} 실행 완료: {execution_time:.2f}초")
            return result
            
        except Exception as e:
            logger.error(f"{self.config.name} 실행 오류: {e}")
            raise
    
    async def ainvoke(
        self,
        input: InputType,
        config: Optional[RunnableConfig] = None,
        **kwargs,
    ) -> OutputType:
        """
        비동기 실행 (Runnable 인터페이스)
        
        Args:
            input: 입력 데이터
            config: Runnable 설정
            **kwargs: 추가 인자
        
        Returns:
            출력 결과
        """
        start_time = datetime.now()
        input_dict = self._normalize_input(input)
        
        try:
            result = await self.chain.ainvoke(input_dict, config=config, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.debug(f"{self.config.name} 비동기 실행 완료: {execution_time:.2f}초")
            return result
            
        except Exception as e:
            logger.error(f"{self.config.name} 비동기 실행 오류: {e}")
            raise
    
    def stream(
        self,
        input: InputType,
        config: Optional[RunnableConfig] = None,
        **kwargs,
    ) -> Iterator[OutputType]:
        """
        스트리밍 실행 (Runnable 인터페이스)
        
        Args:
            input: 입력 데이터
            config: Runnable 설정
            **kwargs: 추가 인자
        
        Yields:
            스트리밍 청크
        """
        input_dict = self._normalize_input(input)
        
        for chunk in self.chain.stream(input_dict, config=config, **kwargs):
            yield chunk
    
    async def astream(
        self,
        input: InputType,
        config: Optional[RunnableConfig] = None,
        **kwargs,
    ) -> AsyncIterator[OutputType]:
        """
        비동기 스트리밍 (Runnable 인터페이스)
        
        Args:
            input: 입력 데이터
            config: Runnable 설정
            **kwargs: 추가 인자
        
        Yields:
            스트리밍 청크
        """
        input_dict = self._normalize_input(input)
        
        async for chunk in self.chain.astream(input_dict, config=config, **kwargs):
            yield chunk
    
    def batch(
        self,
        inputs: List[InputType],
        config: Optional[Union[RunnableConfig, List[RunnableConfig]]] = None,
        **kwargs,
    ) -> List[OutputType]:
        """
        배치 실행 (Runnable 인터페이스)
        
        Args:
            inputs: 입력 데이터 리스트
            config: Runnable 설정
            **kwargs: 추가 인자
        
        Returns:
            출력 결과 리스트
        """
        input_dicts = [self._normalize_input(inp) for inp in inputs]
        return self.chain.batch(input_dicts, config=config, **kwargs)
    
    async def abatch(
        self,
        inputs: List[InputType],
        config: Optional[Union[RunnableConfig, List[RunnableConfig]]] = None,
        **kwargs,
    ) -> List[OutputType]:
        """
        비동기 배치 실행 (Runnable 인터페이스)
        
        Args:
            inputs: 입력 데이터 리스트
            config: Runnable 설정
            **kwargs: 추가 인자
        
        Returns:
            출력 결과 리스트
        """
        input_dicts = [self._normalize_input(inp) for inp in inputs]
        return await self.chain.abatch(input_dicts, config=config, **kwargs)
    
    # =========================================================================
    # LCEL 유틸리티 메서드
    # =========================================================================
    
    def with_fallbacks(
        self,
        fallbacks: List["BaseLangChainAgent"],
        **kwargs,
    ) -> Runnable:
        """
        Fallback Agent 설정
        
        메인 Agent가 실패하면 순차적으로 fallback Agent를 시도합니다.
        
        Args:
            fallbacks: Fallback Agent 리스트
            **kwargs: with_fallbacks 추가 인자
        
        Returns:
            Fallback이 설정된 Runnable
        
        Example:
            ```python
            robust_agent = main_agent.with_fallbacks([backup_agent1, backup_agent2])
            ```
        """
        fallback_chains = [fb.chain for fb in fallbacks]
        return self.chain.with_fallbacks(fallback_chains, **kwargs)
    
    def with_retry(
        self,
        stop_after_attempt: int = 3,
        wait_exponential_multiplier: float = 1.0,
        **kwargs,
    ) -> Runnable:
        """
        재시도 로직 설정
        
        실패 시 지정된 횟수만큼 재시도합니다.
        
        Args:
            stop_after_attempt: 최대 시도 횟수
            wait_exponential_multiplier: 대기 시간 배수
            **kwargs: with_retry 추가 인자
        
        Returns:
            재시도가 설정된 Runnable
        
        Example:
            ```python
            reliable_agent = agent.with_retry(stop_after_attempt=3)
            ```
        """
        return self.chain.with_retry(
            stop_after_attempt=stop_after_attempt,
            wait_exponential_jitter=True,
            **kwargs,
        )
    
    def pipe(
        self,
        *others: Runnable,
        name: Optional[str] = None,
    ) -> RunnableSequence:
        """
        다른 Runnable과 파이프 연결
        
        Args:
            *others: 연결할 Runnable들
            name: 체인 이름
        
        Returns:
            연결된 RunnableSequence
        
        Example:
            ```python
            chain = agent.pipe(parser, formatter)
            ```
        """
        return self.chain.pipe(*others, name=name)
    
    def __or__(self, other: Runnable) -> RunnableSequence:
        """| 연산자로 체인 연결"""
        return self.chain | other
    
    def __ror__(self, other: Runnable) -> RunnableSequence:
        """| 연산자로 체인 연결 (역방향)"""
        return other | self.chain
    
    # =========================================================================
    # 유틸리티 메서드
    # =========================================================================
    
    def bind_tools(
        self,
        tools: List[Any],
    ) -> "BaseLangChainAgent":
        """
        Tool 바인딩
        
        Args:
            tools: Tool 목록
        
        Returns:
            self (체이닝 지원)
        """
        self.tools.extend(tools)
        if hasattr(self.llm, 'bind_tools'):
            self.llm = self.llm.bind_tools(tools)
            self.chain = self._build_chain()  # Chain 재구성
        return self
    
    def update_config(self, **kwargs) -> "BaseLangChainAgent":
        """
        설정 업데이트
        
        Args:
            **kwargs: 업데이트할 설정 값들
        
        Returns:
            self (체이닝 지원)
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        return self
    
    def get_info(self) -> Dict[str, Any]:
        """Agent 정보 반환"""
        return {
            "name": self.config.name,
            "role": self.role.value,
            "llm": str(type(self.llm).__name__),
            "tools_count": len(self.tools),
            "has_memory": self.memory is not None,
            "chain_type": str(type(self.chain).__name__),
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.config.name}, role={self.role.value})"


# =============================================================================
# SimpleChainAgent
# =============================================================================

class SimpleChainAgent(BaseLangChainAgent):
    """
    단순 Chain Agent
    
    Tool 없이 LLM만 사용하는 간단한 Agent입니다.
    Writer, QA 등에 적합합니다.
    
    LCEL Chain: prompt | llm | StrOutputParser
    """
    
    def _build_chain(self) -> Runnable:
        """LCEL Chain 구성"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            MessagesPlaceholder(variable_name="history", optional=True),
            ("human", "{input}"),
        ])
        
        return prompt | self.llm | StrOutputParser()
    
    def _get_system_prompt(self) -> str:
        """기본 시스템 프롬프트"""
        return self.config.system_prompt or "You are a helpful AI assistant."


# =============================================================================
# StructuredOutputAgent
# =============================================================================

class StructuredOutputAgent(BaseLangChainAgent, Generic[OutputType]):
    """
    구조화된 출력 Agent
    
    Pydantic 모델을 사용하여 타입 안전한 출력을 생성합니다.
    Planner, QA 등에 적합합니다.
    
    LCEL Chain: prompt | llm.with_structured_output(schema)
    
    Example:
        ```python
        class PlanOutput(BaseModel):
            steps: List[str]
            summary: str
        
        agent = StructuredOutputAgent(llm, PlanOutput)
        plan: PlanOutput = agent.invoke("프로젝트 계획 수립")
        ```
    """
    
    def __init__(
        self,
        llm: BaseChatModel,
        output_schema: Type[OutputType],
        config: Optional[AgentConfig] = None,
        **kwargs,
    ):
        """
        초기화
        
        Args:
            llm: LangChain LLM 인스턴스
            output_schema: Pydantic 출력 스키마
            config: Agent 설정
            **kwargs: 추가 인자
        """
        self._output_schema = output_schema  # _로 변경 (Runnable.output_schema property 충돌 방지)
        super().__init__(llm, config, **kwargs)
    
    def _build_chain(self) -> Runnable:
        """LCEL Chain 구성 (구조화된 출력)"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            MessagesPlaceholder(variable_name="history", optional=True),
            ("human", "{input}"),
        ])
        
        # 구조화된 출력 LLM
        structured_llm = self.llm.with_structured_output(self._output_schema)
        
        return prompt | structured_llm
    
    def _get_system_prompt(self) -> str:
        """시스템 프롬프트 (스키마 정보 포함)"""
        base_prompt = self.config.system_prompt or "You are a helpful AI assistant."
        
        # 스키마 정보 추가
        if self._output_schema:
            schema_info = f"\n\n[Output Schema]\n{self._output_schema.model_json_schema()}"
            return base_prompt + schema_info
        
        return base_prompt


# =============================================================================
# ToolCallingAgent
# =============================================================================

class ToolCallingAgent(BaseLangChainAgent):
    """
    Tool 호출 Agent
    
    LLM에 Tool을 바인딩하여 외부 기능을 호출합니다.
    Executor 등에 적합합니다.
    
    LCEL Chain: prompt | llm.bind_tools(tools)
    """
    
    def __init__(
        self,
        llm: BaseChatModel,
        tools: List[Any],
        config: Optional[AgentConfig] = None,
        **kwargs,
    ):
        """
        초기화
        
        Args:
            llm: LangChain LLM 인스턴스
            tools: 바인딩할 Tool 리스트
            config: Agent 설정
            **kwargs: 추가 인자
        """
        super().__init__(llm, config, tools=tools, **kwargs)
    
    def _build_chain(self) -> Runnable:
        """LCEL Chain 구성 (Tool 바인딩)"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            MessagesPlaceholder(variable_name="history", optional=True),
            ("human", "{input}"),
        ])
        
        # Tool 바인딩된 LLM
        if self.tools:
            llm_with_tools = self.llm.bind_tools(self.tools)
        else:
            llm_with_tools = self.llm
        
        return prompt | llm_with_tools
    
    def _get_system_prompt(self) -> str:
        """시스템 프롬프트 (Tool 정보 포함)"""
        base_prompt = self.config.system_prompt or "You are a helpful AI assistant with tools."
        
        if self.tools:
            tool_names = [t.name if hasattr(t, 'name') else str(t) for t in self.tools]
            tool_info = f"\n\n[Available Tools]: {', '.join(tool_names)}"
            return base_prompt + tool_info
        
        return base_prompt
