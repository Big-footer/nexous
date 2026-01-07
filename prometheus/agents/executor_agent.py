"""
ExecutorAgent - 실행 Agent

이 파일의 책임:
- 계획된 단계 실행
- Tool 호출 및 결과 처리
- 재시도 로직
- 실행 상태 관리
"""

from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field
import json
import asyncio
import time

from prometheus.agents.base import (
    BaseAgent,
    AgentConfig,
    AgentInput,
    AgentOutput,
    AgentState,
)
from prometheus.llm.base import Message, MessageRole, LLMResponse


class ExecutionStatus(str, Enum):
    """실행 상태"""
    
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ToolCallResult(BaseModel):
    """Tool 호출 결과"""
    
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    success: bool = True
    error: Optional[str] = None
    execution_time: float = 0.0


class StepExecutionResult(BaseModel):
    """단계 실행 결과"""
    
    step_id: str
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    result: Any = None
    tool_calls: List[ToolCallResult] = Field(default_factory=list)
    llm_response: Optional[str] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    retry_count: int = 0


class ExecutorConfig(AgentConfig):
    """Executor 설정"""
    
    name: str = "ExecutorAgent"
    max_tool_calls: int = 10
    tool_timeout: float = 60.0
    retry_count: int = 3
    retry_delay: float = 1.0


class ExecutorAgent(BaseAgent):
    """
    실행 Agent
    
    계획된 단계를 실행하고 Tool을 호출합니다.
    재시도 로직과 오류 처리를 담당합니다.
    """
    
    agent_type: str = "executor"
    
    EXECUTION_PROMPT = """You are an execution agent. Your task is to execute the given step using available tools.

Step to execute:
- Title: {step_title}
- Description: {step_description}

Available tools:
{tool_descriptions}

Context from previous steps:
{context}

Instructions:
1. Analyze what needs to be done
2. Use the appropriate tools to complete the task
3. If no tool is needed, provide your response directly
4. Report the result clearly

Execute this step now."""

    def __init__(
        self,
        config: Optional[ExecutorConfig] = None,
        **kwargs: Any,
    ) -> None:
        """
        ExecutorAgent 초기화
        
        Args:
            config: Executor 설정
            **kwargs: 추가 인자
        """
        super().__init__(config=config or ExecutorConfig(), **kwargs)
        self._tool_call_history: List[ToolCallResult] = []
    
    def _default_system_prompt(self) -> str:
        """기본 시스템 프롬프트"""
        return """You are an expert execution agent. Your role is to:
1. Execute assigned tasks efficiently and accurately
2. Use available tools when needed
3. Handle errors gracefully and retry when appropriate
4. Report results clearly and completely

When you need to use a tool, call it with the correct parameters.
Always verify the results before reporting completion."""
    
    async def run(
        self,
        input: AgentInput,
    ) -> AgentOutput:
        """
        실행
        
        Args:
            input: Agent 입력 (task = 실행할 내용)
            
        Returns:
            Agent 출력
        """
        start_time = time.time()
        self._set_state(AgentState.RUNNING)
        self._tool_call_history.clear()
        
        try:
            # 단계 정보 추출
            step_info = input.context.get("step", {})
            step_id = step_info.get("step_id", "direct_execution")
            
            # 실행
            result = await self.execute_step(
                step_id=step_id,
                step_title=step_info.get("title", "Direct Task"),
                step_description=input.task,
                context=input.context,
            )
            
            execution_time = time.time() - start_time
            self._set_state(AgentState.COMPLETED if result.status == ExecutionStatus.SUCCESS else AgentState.FAILED)
            
            return AgentOutput(
                result=result,
                success=result.status == ExecutionStatus.SUCCESS,
                error=result.error,
                messages=self._messages.copy(),
                execution_time=execution_time,
                metadata={
                    "step_id": step_id,
                    "tool_calls_count": len(result.tool_calls),
                },
            )
            
        except Exception as e:
            self._set_state(AgentState.FAILED)
            return AgentOutput.error_output(
                error=str(e),
                messages=self._messages.copy(),
            )
    
    async def execute_step(
        self,
        step_id: str,
        step_title: str,
        step_description: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> StepExecutionResult:
        """
        단계 실행
        
        Args:
            step_id: 단계 ID
            step_title: 단계 제목
            step_description: 단계 설명
            context: 컨텍스트
            
        Returns:
            실행 결과
        """
        start_time = time.time()
        tool_calls: List[ToolCallResult] = []
        retry_count = 0
        
        while retry_count <= self.config.retry_count:
            try:
                # Tool 설명 생성
                tool_descriptions = self._format_tool_descriptions()
                
                # 프롬프트 생성
                prompt = self.EXECUTION_PROMPT.format(
                    step_title=step_title,
                    step_description=step_description,
                    tool_descriptions=tool_descriptions,
                    context=json.dumps(context or {}, ensure_ascii=False, indent=2),
                )
                
                # 메시지 구성
                messages = [
                    Message.system(self.get_system_prompt()),
                    Message.user(prompt),
                ]
                
                # 이전 대화 추가
                messages.extend(self._messages)
                
                # LLM 호출 (Tool 포함)
                response = await self._call_llm_with_tools(messages)
                
                # Tool 호출 처리
                if response.has_tool_calls():
                    tool_results = await self._process_tool_calls(response.tool_calls)
                    tool_calls.extend(tool_results)
                    
                    # Tool 결과를 메시지에 추가
                    self._add_message(Message.assistant(response.content, response.tool_calls))
                    
                    for tr in tool_results:
                        self._add_message(Message.tool(
                            content=json.dumps(tr.result, ensure_ascii=False) if tr.result else tr.error,
                            tool_call_id=response.tool_calls[tool_results.index(tr)].get("id", ""),
                        ))
                    
                    # 추가 LLM 호출 (결과 요약)
                    final_response = await self._call_llm(
                        messages + self._messages[-len(tool_results)*2:]
                    )
                    llm_result = final_response.content
                else:
                    llm_result = response.content
                    self._add_message(Message.assistant(response.content))
                
                return StepExecutionResult(
                    step_id=step_id,
                    status=ExecutionStatus.SUCCESS,
                    result=llm_result,
                    tool_calls=tool_calls,
                    llm_response=llm_result,
                    execution_time=time.time() - start_time,
                    retry_count=retry_count,
                )
                
            except Exception as e:
                retry_count += 1
                if retry_count <= self.config.retry_count:
                    await asyncio.sleep(self.config.retry_delay)
                else:
                    return StepExecutionResult(
                        step_id=step_id,
                        status=ExecutionStatus.FAILED,
                        error=str(e),
                        tool_calls=tool_calls,
                        execution_time=time.time() - start_time,
                        retry_count=retry_count,
                    )
        
        # Should not reach here
        return StepExecutionResult(
            step_id=step_id,
            status=ExecutionStatus.FAILED,
            error="Max retries exceeded",
            execution_time=time.time() - start_time,
        )
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> ToolCallResult:
        """
        Tool 호출
        
        Args:
            tool_name: Tool 이름
            arguments: 인자
            
        Returns:
            Tool 호출 결과
        """
        start_time = time.time()
        
        try:
            result = await self._execute_tool(tool_name, arguments)
            
            tool_result = ToolCallResult(
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                success=True,
                execution_time=time.time() - start_time,
            )
            
        except asyncio.TimeoutError:
            tool_result = ToolCallResult(
                tool_name=tool_name,
                arguments=arguments,
                success=False,
                error="Tool execution timeout",
                execution_time=time.time() - start_time,
            )
            
        except Exception as e:
            tool_result = ToolCallResult(
                tool_name=tool_name,
                arguments=arguments,
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )
        
        self._tool_call_history.append(tool_result)
        return tool_result
    
    async def _process_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
    ) -> List[ToolCallResult]:
        """
        Tool 호출 목록 처리
        
        Args:
            tool_calls: Tool 호출 목록
            
        Returns:
            Tool 호출 결과 목록
        """
        results = []
        
        for tc in tool_calls:
            func = tc.get("function", {})
            tool_name = func.get("name", "")
            
            # arguments 파싱
            args_str = func.get("arguments", "{}")
            try:
                if isinstance(args_str, str):
                    arguments = json.loads(args_str)
                else:
                    arguments = args_str
            except json.JSONDecodeError:
                arguments = {}
            
            # Tool 호출
            result = await self.call_tool(tool_name, arguments)
            results.append(result)
        
        return results
    
    def _format_tool_descriptions(self) -> str:
        """
        Tool 설명 포맷팅
        
        Returns:
            Tool 설명 문자열
        """
        if not self._tools:
            return "No tools available."
        
        descriptions = []
        for name, tool in self._tools.items():
            desc = getattr(tool, 'description', f"Tool: {name}")
            descriptions.append(f"- {name}: {desc}")
        
        return "\n".join(descriptions)
    
    async def execute_with_retry(
        self,
        func,
        max_retries: int = 3,
        delay: float = 1.0,
    ) -> Any:
        """
        재시도 로직이 포함된 실행
        
        Args:
            func: 실행할 비동기 함수
            max_retries: 최대 재시도 횟수
            delay: 재시도 간 대기 시간
            
        Returns:
            함수 실행 결과
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                return await func()
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    await asyncio.sleep(delay * (attempt + 1))
        
        raise last_error
    
    def get_tool_call_history(self) -> List[ToolCallResult]:
        """
        Tool 호출 기록 조회
        
        Returns:
            Tool 호출 결과 목록
        """
        return self._tool_call_history.copy()
    
    def clear_tool_call_history(self) -> None:
        """Tool 호출 기록 초기화"""
        self._tool_call_history.clear()
