"""
NEXOUS Tool - File Read

파일 읽기 도구

입력 형식:
{
  "path": "data/input.csv"
}
"""

from __future__ import annotations

import time
import logging
from pathlib import Path

from .base import ToolResult, make_result

logger = logging.getLogger(__name__)


class FileReadTool:
    """
    파일 읽기 Tool
    
    입력: {"path": "data/input.csv"}
    """
    
    name: str = "file_read"
    description: str = "Read contents from a file"
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    def __init__(self, base_dir: str = None):
        self._base_dir = Path(base_dir) if base_dir else Path.cwd()
    
    def run(self, path: str, **kwargs) -> ToolResult:
        """
        파일 읽기
        
        Args:
            path: 파일 경로
            
        Returns:
            ToolResult
        """
        start_time = time.time()
        encoding = kwargs.get("encoding", "utf-8")
        
        try:
            file_path = self._resolve_path(path)
            
            if not file_path.exists():
                return make_result(
                    ok=False,
                    output=None,
                    error=f"File not found: {path}",
                    latency_ms=int((time.time() - start_time) * 1000),
                    tool_name=self.name,
                )
            
            if file_path.is_dir():
                return make_result(
                    ok=False,
                    output=None,
                    error=f"Path is a directory: {path}",
                    latency_ms=int((time.time() - start_time) * 1000),
                    tool_name=self.name,
                )
            
            file_size = file_path.stat().st_size
            if file_size > self.MAX_FILE_SIZE:
                return make_result(
                    ok=False,
                    output=None,
                    error=f"File too large: {file_size} bytes",
                    latency_ms=int((time.time() - start_time) * 1000),
                    tool_name=self.name,
                )
            
            content = file_path.read_text(encoding=encoding)
            latency_ms = int((time.time() - start_time) * 1000)
            
            logger.info(f"[FileRead] {path} | {len(content)} chars | {latency_ms}ms")
            
            return make_result(
                ok=True,
                output=content,
                error=None,
                latency_ms=latency_ms,
                tool_name=self.name,
                file_size=file_size,
            )
            
        except UnicodeDecodeError as e:
            return make_result(
                ok=False,
                output=None,
                error=f"Encoding error: {e}",
                latency_ms=int((time.time() - start_time) * 1000),
                tool_name=self.name,
            )
            
        except Exception as e:
            logger.error(f"[FileRead] Error: {e}")
            return make_result(
                ok=False,
                output=None,
                error=str(e),
                latency_ms=int((time.time() - start_time) * 1000),
                tool_name=self.name,
            )
    
    def _resolve_path(self, path: str) -> Path:
        file_path = Path(path)
        if file_path.is_absolute():
            return file_path.resolve()
        return (self._base_dir / path).resolve()
