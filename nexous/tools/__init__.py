"""
NEXOUS Tools Package

LEVEL 1: 3개 Tool만 허용
- python_exec: Python 코드 실행
- file_read: 파일 읽기
- file_write: 파일 쓰기

Agent는 반드시 Registry를 통해서만 Tool을 가져온다.
"""

from .base import Tool, ToolResult, ToolError, make_result
from .python_exec import PythonExecTool
from .file_read import FileReadTool
from .file_write import FileWriteTool
from .registry import ToolRegistry, get_registry, ALLOWED_TOOLS

__all__ = [
    # Base (고정 계약)
    "Tool",
    "ToolResult",
    "ToolError",
    "make_result",
    # Tools
    "PythonExecTool",
    "FileReadTool",
    "FileWriteTool",
    # Registry (단일 진입점)
    "ToolRegistry",
    "get_registry",
    "ALLOWED_TOOLS",
]
