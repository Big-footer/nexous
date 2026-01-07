"""
NEXOUS Tool - Base Interface

Tool 인터페이스 계약 (고정)

LEVEL 1 철학:
- Tool은 Agent만 호출한다.
- Runner/GUI는 Tool을 모른다.
- Tool은 결정하지 않는다 (판단/계획 ❌).
- Tool은 작업만 수행한다.
"""

from __future__ import annotations

from typing import TypedDict, Protocol, Optional, Dict, Any


class ToolResult(TypedDict):
    """
    Tool 실행 결과 (고정 계약)
    
    모든 Tool은 이 타입을 반환해야 한다.
    """
    ok: bool
    output: Optional[str]
    error: Optional[str]
    metadata: Dict[str, Any]


class Tool(Protocol):
    """
    Tool 인터페이스 (고정 계약)
    
    모든 Tool은 이 Protocol을 구현해야 한다.
    """
    name: str
    description: str
    
    def run(self, **kwargs) -> ToolResult:
        """
        Tool 실행
        
        Args:
            **kwargs: Tool별 파라미터
            
        Returns:
            ToolResult
        """
        ...


class ToolError(Exception):
    """Tool 실행 오류"""
    
    def __init__(
        self,
        message: str,
        tool_name: str = "",
        recoverable: bool = False,
    ):
        super().__init__(message)
        self.tool_name = tool_name
        self.recoverable = recoverable


def make_result(
    ok: bool,
    output: Optional[str] = None,
    error: Optional[str] = None,
    **metadata
) -> ToolResult:
    """ToolResult 생성 헬퍼"""
    return ToolResult(
        ok=ok,
        output=output,
        error=error,
        metadata=metadata,
    )
