"""
PROMETHEUS ExecutorAgent (LangChain)

계획을 실행하고 Tool을 호출하는 Agent입니다.
LangChain의 Tool-calling 기능을 활용합니다.
"""

from typing import Any, Dict, List, Optional, Callable
from pydantic import BaseModel, Field
import json

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool, BaseTool, StructuredTool

from prometheus.agents.langchain_base import (
    BaseLangChainAgent,
    AgentConfig,
    AgentRole,
    AgentOutput,
)
from prometheus.tools.secure_executor import secure_python_exec, ExecutionMode, get_executor


# =============================================================================
# 출력 스키마
# =============================================================================

class ToolCallResult(BaseModel):
    """Tool 호출 결과"""
    tool_name: str = Field(description="Tool 이름")
    arguments: Dict[str, Any] = Field(description="Tool 인자")
    result: Any = Field(default=None, description="실행 결과")
    success: bool = Field(default=True, description="성공 여부")
    error: Optional[str] = Field(default=None, description="에러 메시지")
    execution_time: float = Field(default=0.0, description="실행 시간(초)")


class StepResult(BaseModel):
    """단계 실행 결과"""
    step_id: int = Field(description="단계 ID")
    action: str = Field(description="수행한 작업")
    status: str = Field(default="success", description="상태 (success, failed, skipped)")
    output: Any = Field(default=None, description="출력")
    tool_calls: List[ToolCallResult] = Field(default_factory=list, description="Tool 호출 기록")
    error: Optional[str] = Field(default=None, description="에러 메시지")


class ExecutionResult(BaseModel):
    """Executor Agent 전체 실행 결과"""
    step_results: List[StepResult] = Field(description="각 단계 결과")
    success_count: int = Field(default=0, description="성공한 단계 수")
    fail_count: int = Field(default=0, description="실패한 단계 수")
    artifacts: List[str] = Field(default_factory=list, description="생성된 산출물 경로")
    total_execution_time: float = Field(default=0.0, description="총 실행 시간(초)")
    summary: str = Field(default="", description="실행 요약")


# =============================================================================
# 기본 Tool 정의
# =============================================================================

@tool
def python_exec(code: str) -> str:
    """
    Python 코드를 안전하게 실행합니다.
    
    Docker 샌드박스 또는 제한된 환경에서 실행되며,
    위험한 작업(파일 접근, 네트워크, 시스템 명령)은 차단됩니다.
    
    Args:
        code: 실행할 Python 코드
    
    Returns:
        실행 결과 문자열
    """
    return secure_python_exec(code)


@tool
def file_write(filepath: str, content: str) -> str:
    """
    파일을 작성합니다.
    
    Args:
        filepath: 파일 경로
        content: 파일 내용
    
    Returns:
        결과 메시지
    """
    try:
        from pathlib import Path
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"파일 작성 완료: {filepath}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def file_read(filepath: str) -> str:
    """
    파일을 읽습니다.
    
    Args:
        filepath: 파일 경로
    
    Returns:
        파일 내용
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def web_search(query: str) -> str:
    """
    웹 검색을 수행합니다. (스텁)
    
    Args:
        query: 검색어
    
    Returns:
        검색 결과
    """
    # TODO: 실제 웹 검색 구현
    return f"웹 검색 결과 (스텁): '{query}'에 대한 검색 결과입니다."


@tool
def rag_search(query: str, top_k: int = 5) -> str:
    """
    RAG 문서 검색을 수행합니다. (스텁)
    
    Args:
        query: 검색 쿼리
        top_k: 반환할 결과 수
    
    Returns:
        검색 결과
    """
    # TODO: 실제 RAG 검색 구현
    return f"RAG 검색 결과 (스텁): '{query}'에 대한 {top_k}개 문서를 찾았습니다."


# 기본 Tool 목록
DEFAULT_TOOLS = [python_exec, file_write, file_read, web_search, rag_search]


# =============================================================================
# ExecutorAgent
# =============================================================================

EXECUTOR_SYSTEM_PROMPT = """당신은 PROMETHEUS의 Executor Agent입니다.
주어진 계획을 실행하고 Tool을 호출하여 작업을 수행합니다.

## 역할
1. 계획의 각 단계를 순서대로 실행
2. 필요한 Tool을 호출하여 작업 수행
3. 실행 결과를 수집하고 정리
4. 오류 발생 시 적절히 처리

## 사용 가능한 Tool
- python_exec: Python 코드 실행
- file_write: 파일 작성
- file_read: 파일 읽기
- web_search: 웹 검색
- rag_search: 문서 검색

## 실행 원칙
1. 각 단계를 신중하게 실행
2. Tool 호출 전 입력 데이터 검증
3. 실행 결과를 명확하게 기록
4. 오류 발생 시 재시도 또는 대안 실행

각 단계를 실행한 후 결과를 보고하세요.
"""


class ExecutorAgent(BaseLangChainAgent):
    """
    Executor Agent
    
    계획을 실행하고 Tool을 호출합니다.
    LangChain의 Tool-calling 기능을 활용합니다.
    """
    
    role = AgentRole.EXECUTOR
    
    def __init__(
        self,
        llm: BaseChatModel,
        config: Optional[AgentConfig] = None,
        tools: Optional[List[BaseTool]] = None,
        **kwargs,
    ):
        """
        초기화
        
        Args:
            llm: LangChain LLM (GPT 추천)
            config: Agent 설정
            tools: 사용할 Tool 목록
        """
        if config is None:
            config = AgentConfig(
                name="ExecutorAgent",
                role=AgentRole.EXECUTOR,
                system_prompt=EXECUTOR_SYSTEM_PROMPT,
            )
        
        # 기본 Tool 추가
        if tools is None:
            tools = DEFAULT_TOOLS.copy()
        
        super().__init__(
            llm=llm,
            config=config,
            tools=tools,
            **kwargs,
        )
    
    def _build_chain(self) -> "Runnable":
        """LCEL Chain 구성 (Tool-calling)"""
        from langchain_core.runnables import Runnable
        
        # Tool 바인딩
        if self.tools:
            self.llm_with_tools = self.llm.bind_tools(self.tools)
        else:
            self.llm_with_tools = self.llm
        
        # 프롬프트
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            MessagesPlaceholder(variable_name="messages"),
        ])
        
        # Runnable 체인 반환
        return self.prompt | self.llm_with_tools
    
    def _get_system_prompt(self) -> str:
        """시스템 프롬프트"""
        return self.config.system_prompt or EXECUTOR_SYSTEM_PROMPT
    
    def execute_plan(
        self,
        plan: Dict[str, Any],
        max_iterations: int = 10,
    ) -> ExecutionResult:
        """
        계획 실행
        
        Args:
            plan: 실행할 계획 (PlanOutput 형태)
            max_iterations: 최대 반복 횟수
        
        Returns:
            ExecutionResult
        """
        from datetime import datetime
        start_time = datetime.now()
        
        steps = plan.get("steps", [])
        step_results = []
        artifacts = []
        
        messages = [
            HumanMessage(content=f"다음 계획을 실행해주세요:\n\n{json.dumps(plan, ensure_ascii=False, indent=2)}")
        ]
        
        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            
            # LLM 호출
            response = self.chain.invoke({"messages": messages})
            
            # Tool 호출 처리
            if hasattr(response, 'tool_calls') and response.tool_calls:
                tool_results = []
                
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    # Tool 실행
                    tool_result = self._execute_tool(tool_name, tool_args)
                    tool_results.append(tool_result)
                    
                    # ToolMessage 추가
                    messages.append(response)
                    messages.append(ToolMessage(
                        content=str(tool_result.result),
                        tool_call_id=tool_call["id"],
                    ))
                
                # StepResult 생성
                step_results.append(StepResult(
                    step_id=len(step_results) + 1,
                    action=f"Tool 호출: {[tr.tool_name for tr in tool_results]}",
                    status="success" if all(tr.success for tr in tool_results) else "failed",
                    output=[tr.result for tr in tool_results],
                    tool_calls=tool_results,
                ))
            else:
                # Tool 호출 없이 응답
                messages.append(response)
                
                # 최종 응답으로 판단
                if hasattr(response, 'content') and response.content:
                    step_results.append(StepResult(
                        step_id=len(step_results) + 1,
                        action="최종 응답 생성",
                        status="success",
                        output=response.content,
                    ))
                    break
        
        total_time = (datetime.now() - start_time).total_seconds()
        success_count = len([r for r in step_results if r.status == "success"])
        fail_count = len([r for r in step_results if r.status == "failed"])
        
        return ExecutionResult(
            step_results=step_results,
            success_count=success_count,
            fail_count=fail_count,
            artifacts=artifacts,
            total_execution_time=total_time,
            summary=f"총 {len(step_results)}개 단계 실행: {success_count}개 성공, {fail_count}개 실패",
        )
    
    def _execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
    ) -> ToolCallResult:
        """
        Tool 실행
        
        Args:
            tool_name: Tool 이름
            tool_args: Tool 인자
        
        Returns:
            ToolCallResult
        """
        from datetime import datetime
        start_time = datetime.now()
        
        # Tool 찾기
        tool = None
        for t in self.tools:
            if t.name == tool_name:
                tool = t
                break
        
        if tool is None:
            return ToolCallResult(
                tool_name=tool_name,
                arguments=tool_args,
                success=False,
                error=f"Tool not found: {tool_name}",
            )
        
        try:
            result = tool.invoke(tool_args)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ToolCallResult(
                tool_name=tool_name,
                arguments=tool_args,
                result=result,
                success=True,
                execution_time=execution_time,
            )
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ToolCallResult(
                tool_name=tool_name,
                arguments=tool_args,
                success=False,
                error=str(e),
                execution_time=execution_time,
            )


# =============================================================================
# 팩토리 함수
# =============================================================================

def create_executor_agent(
    llm: Optional[BaseChatModel] = None,
    provider: str = "openai",
    model: Optional[str] = None,
    tools: Optional[List[BaseTool]] = None,
) -> ExecutorAgent:
    """
    ExecutorAgent 생성 팩토리
    
    Args:
        llm: LLM 인스턴스 (없으면 생성)
        provider: LLM 프로바이더
        model: 모델명
        tools: Tool 목록
    
    Returns:
        ExecutorAgent
    """
    if llm is None:
        if provider == "openai":
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model=model or "gpt-4o",
                temperature=0.3,  # 실행은 정확성이 중요
            )
        elif provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(
                model=model or "claude-sonnet-4-20250514",
                temperature=0.3,
            )
        elif provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model=model or "gemini-2.0-flash",
                temperature=0.3,
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    return ExecutorAgent(llm=llm, tools=tools)
