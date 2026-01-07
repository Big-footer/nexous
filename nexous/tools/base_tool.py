"""
NEXOUS Tool - Base

Tool 기본 인터페이스
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ToolResult:
    """Tool 실행 결과"""
    success: bool
    output: Any
    error: Optional[str] = None
    latency_ms: int = 0


class BaseTool(ABC):
    """Tool 기본 클래스"""
    
    name: str = "base_tool"
    description: str = "Base tool"
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Tool 실행"""
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"
