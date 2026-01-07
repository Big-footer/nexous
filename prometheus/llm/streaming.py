"""
PROMETHEUS Streaming Support

Agent와 Workflow의 스트리밍 응답을 지원합니다.
"""

from typing import AsyncIterator, Iterator, Dict, Any, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)


class StreamEventType(str, Enum):
    """스트림 이벤트 타입"""
    START = "start"           # 시작
    TOKEN = "token"           # 토큰 생성
    TOOL_CALL = "tool_call"   # Tool 호출 시작
    TOOL_RESULT = "tool_result"  # Tool 결과
    AGENT_START = "agent_start"  # Agent 시작
    AGENT_END = "agent_end"      # Agent 종료
    ERROR = "error"           # 에러
    END = "end"               # 종료


@dataclass
class StreamEvent:
    """스트림 이벤트"""
    type: StreamEventType
    content: Any = None
    agent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "type": self.type.value,
            "content": self.content,
            "agent": self.agent,
            "metadata": self.metadata or {},
        }


class StreamingHandler:
    """
    스트리밍 응답 핸들러
    
    Agent의 스트리밍 출력을 처리합니다.
    
    Example:
        ```python
        handler = StreamingHandler(
            on_token=lambda t: print(t, end="", flush=True),
            on_agent_start=lambda a: print(f"\\n[{a}] 시작"),
        )
        
        async for event in agent.astream("요청"):
            handler.handle(event)
        ```
    """
    
    def __init__(
        self,
        on_token: Optional[Callable[[str], None]] = None,
        on_tool_call: Optional[Callable[[str, Dict], None]] = None,
        on_tool_result: Optional[Callable[[str, Any], None]] = None,
        on_agent_start: Optional[Callable[[str], None]] = None,
        on_agent_end: Optional[Callable[[str, Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        on_end: Optional[Callable[[Any], None]] = None,
    ):
        """
        초기화
        
        Args:
            on_token: 토큰 생성 콜백
            on_tool_call: Tool 호출 콜백
            on_tool_result: Tool 결과 콜백
            on_agent_start: Agent 시작 콜백
            on_agent_end: Agent 종료 콜백
            on_error: 에러 콜백
            on_end: 종료 콜백
        """
        self.on_token = on_token
        self.on_tool_call = on_tool_call
        self.on_tool_result = on_tool_result
        self.on_agent_start = on_agent_start
        self.on_agent_end = on_agent_end
        self.on_error = on_error
        self.on_end = on_end
        
        self._buffer = ""
        self._current_agent = None
    
    def handle(self, event: Union[StreamEvent, Dict, str]) -> None:
        """
        이벤트 처리
        
        Args:
            event: StreamEvent, 딕셔너리, 또는 문자열
        """
        # 문자열인 경우 토큰으로 처리
        if isinstance(event, str):
            self._handle_token(event)
            return
        
        # 딕셔너리인 경우 StreamEvent로 변환
        if isinstance(event, dict):
            event_type = event.get("type", "token")
            if isinstance(event_type, str):
                event_type = StreamEventType(event_type)
            event = StreamEvent(
                type=event_type,
                content=event.get("content"),
                agent=event.get("agent"),
                metadata=event.get("metadata"),
            )
        
        # 이벤트 타입별 처리
        handlers = {
            StreamEventType.TOKEN: self._handle_token,
            StreamEventType.TOOL_CALL: self._handle_tool_call,
            StreamEventType.TOOL_RESULT: self._handle_tool_result,
            StreamEventType.AGENT_START: self._handle_agent_start,
            StreamEventType.AGENT_END: self._handle_agent_end,
            StreamEventType.ERROR: self._handle_error,
            StreamEventType.END: self._handle_end,
        }
        
        handler = handlers.get(event.type)
        if handler:
            handler(event)
    
    def _handle_token(self, event: Union[StreamEvent, str]) -> None:
        """토큰 처리"""
        token = event.content if isinstance(event, StreamEvent) else event
        self._buffer += token
        
        if self.on_token:
            self.on_token(token)
    
    def _handle_tool_call(self, event: StreamEvent) -> None:
        """Tool 호출 처리"""
        if self.on_tool_call and event.content:
            tool_name = event.content.get("name", "unknown")
            tool_args = event.content.get("args", {})
            self.on_tool_call(tool_name, tool_args)
    
    def _handle_tool_result(self, event: StreamEvent) -> None:
        """Tool 결과 처리"""
        if self.on_tool_result and event.content:
            tool_name = event.content.get("name", "unknown")
            result = event.content.get("result")
            self.on_tool_result(tool_name, result)
    
    def _handle_agent_start(self, event: StreamEvent) -> None:
        """Agent 시작 처리"""
        self._current_agent = event.agent
        if self.on_agent_start:
            self.on_agent_start(event.agent)
    
    def _handle_agent_end(self, event: StreamEvent) -> None:
        """Agent 종료 처리"""
        if self.on_agent_end:
            self.on_agent_end(event.agent, event.content)
        self._current_agent = None
    
    def _handle_error(self, event: StreamEvent) -> None:
        """에러 처리"""
        if self.on_error:
            error = event.content if isinstance(event.content, Exception) else Exception(str(event.content))
            self.on_error(error)
    
    def _handle_end(self, event: StreamEvent) -> None:
        """종료 처리"""
        if self.on_end:
            self.on_end(event.content)
    
    @property
    def buffer(self) -> str:
        """버퍼 내용 반환"""
        return self._buffer
    
    def clear_buffer(self) -> str:
        """버퍼 초기화 및 내용 반환"""
        content = self._buffer
        self._buffer = ""
        return content


def stream_to_string(stream: Iterator) -> str:
    """
    스트림을 문자열로 변환
    
    Args:
        stream: 스트림 이터레이터
    
    Returns:
        결합된 문자열
    """
    result = []
    for chunk in stream:
        if isinstance(chunk, str):
            result.append(chunk)
        elif hasattr(chunk, 'content'):
            result.append(chunk.content)
        elif isinstance(chunk, dict):
            result.append(str(chunk.get('content', '')))
    return ''.join(result)


async def astream_to_string(stream: AsyncIterator) -> str:
    """
    비동기 스트림을 문자열로 변환
    
    Args:
        stream: 비동기 스트림 이터레이터
    
    Returns:
        결합된 문자열
    """
    result = []
    async for chunk in stream:
        if isinstance(chunk, str):
            result.append(chunk)
        elif hasattr(chunk, 'content'):
            result.append(chunk.content)
        elif isinstance(chunk, dict):
            result.append(str(chunk.get('content', '')))
    return ''.join(result)


def create_console_handler() -> StreamingHandler:
    """
    콘솔 출력용 스트리밍 핸들러 생성
    
    Returns:
        StreamingHandler
    """
    return StreamingHandler(
        on_token=lambda t: print(t, end="", flush=True),
        on_agent_start=lambda a: print(f"\n🔄 [{a}] 시작...", flush=True),
        on_agent_end=lambda a, r: print(f"\n✅ [{a}] 완료", flush=True),
        on_tool_call=lambda n, a: print(f"\n🔧 Tool: {n}", flush=True),
        on_error=lambda e: print(f"\n❌ 에러: {e}", flush=True),
        on_end=lambda r: print("\n--- 완료 ---", flush=True),
    )


# =============================================================================
# Workflow 스트리밍 지원
# =============================================================================

async def stream_workflow(
    workflow,
    request: str,
    project_name: str = "unnamed",
    handler: Optional[StreamingHandler] = None,
) -> Dict[str, Any]:
    """
    워크플로우 스트리밍 실행
    
    Args:
        workflow: PrometheusWorkflow 인스턴스
        request: 사용자 요청
        project_name: 프로젝트 이름
        handler: 스트리밍 핸들러 (없으면 기본 핸들러 사용)
    
    Returns:
        최종 State
    
    Example:
        ```python
        workflow = PrometheusWorkflow()
        handler = create_console_handler()
        
        result = await stream_workflow(workflow, "코드 작성", handler=handler)
        ```
    """
    if handler is None:
        handler = create_console_handler()
    
    # START 이벤트
    handler.handle(StreamEvent(
        type=StreamEventType.START,
        content=request,
        metadata={"project": project_name},
    ))
    
    final_state = None
    
    try:
        # 워크플로우 스트리밍 실행
        async for event in workflow.astream(request, project_name):
            # LangGraph 이벤트를 StreamEvent로 변환
            if isinstance(event, dict):
                # Agent 노드 이벤트
                for node_name, node_output in event.items():
                    # Agent 시작
                    handler.handle(StreamEvent(
                        type=StreamEventType.AGENT_START,
                        agent=node_name,
                    ))
                    
                    # 결과 처리
                    if isinstance(node_output, dict):
                        # 메시지가 있으면 토큰으로 처리
                        messages = node_output.get("messages", [])
                        for msg in messages:
                            if hasattr(msg, 'content'):
                                handler.handle(StreamEvent(
                                    type=StreamEventType.TOKEN,
                                    content=msg.content,
                                    agent=node_name,
                                ))
                    
                    # Agent 종료
                    handler.handle(StreamEvent(
                        type=StreamEventType.AGENT_END,
                        agent=node_name,
                        content=node_output,
                    ))
                    
                    final_state = node_output
            else:
                # 문자열 토큰
                handler.handle(StreamEvent(
                    type=StreamEventType.TOKEN,
                    content=str(event),
                ))
    
    except Exception as e:
        handler.handle(StreamEvent(
            type=StreamEventType.ERROR,
            content=e,
        ))
        raise
    
    # END 이벤트
    handler.handle(StreamEvent(
        type=StreamEventType.END,
        content=final_state,
    ))
    
    return final_state
