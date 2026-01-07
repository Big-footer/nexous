"""
NEXOUS Tool - Registry (단일 진입점)

Agent는 반드시 Registry를 통해서만 Tool을 가져온다.

LEVEL 1: 3개 Tool만 등록
- python_exec
- file_read
- file_write
"""

from __future__ import annotations

import logging
from typing import Dict, Type, List

from .base import Tool, ToolError
from .python_exec import PythonExecTool
from .file_read import FileReadTool
from .file_write import FileWriteTool

logger = logging.getLogger(__name__)


# LEVEL 1: 허용된 Tool (3개만)
ALLOWED_TOOLS: List[str] = ["python_exec", "file_read", "file_write"]


class ToolRegistry:
    """
    Tool Registry (단일 진입점)
    
    Agent는 반드시 이 Registry를 통해서만 Tool을 가져온다.
    
    LEVEL 1: 3개 Tool만 등록/사용 가능
    """
    
    # Tool 클래스 매핑
    _TOOL_CLASSES: Dict[str, Type] = {
        "python_exec": PythonExecTool,
        "file_read": FileReadTool,
        "file_write": FileWriteTool,
    }
    
    # 싱글톤 인스턴스 캐시
    _instances: Dict[str, Tool] = {}
    
    def get(self, name: str) -> Tool:
        """
        Tool 인스턴스 반환 (단일 진입점)
        
        Args:
            name: Tool 이름
            
        Returns:
            Tool 인스턴스
            
        Raises:
            ToolError: Tool이 없거나 허용되지 않은 경우
        """
        if name not in ALLOWED_TOOLS:
            raise ToolError(
                f"Tool '{name}' not allowed. Allowed: {ALLOWED_TOOLS}",
                tool_name=name,
            )
        
        if name in self._instances:
            return self._instances[name]
        
        tool_class = self._TOOL_CLASSES[name]
        tool = tool_class()
        self._instances[name] = tool
        
        logger.debug(f"[ToolRegistry] Created tool: {name}")
        return tool
    
    def list_tools(self) -> List[str]:
        """사용 가능한 Tool 목록"""
        return ALLOWED_TOOLS.copy()
    
    def is_available(self, name: str) -> bool:
        """Tool 사용 가능 여부"""
        return name in ALLOWED_TOOLS
    
    def clear_cache(self) -> None:
        """인스턴스 캐시 초기화 (테스트용)"""
        self._instances.clear()


# 전역 싱글톤 인스턴스
_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Registry 싱글톤 반환"""
    return _registry
