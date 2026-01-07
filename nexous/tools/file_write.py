"""
NEXOUS Tool - File Write

파일 쓰기 도구

입력 형식:
{
  "path": "outputs/result.txt",
  "content": "Hello World"
}
"""

from __future__ import annotations

import time
import logging
from pathlib import Path

from .base import ToolResult, make_result

logger = logging.getLogger(__name__)


class FileWriteTool:
    """
    파일 쓰기 Tool
    
    입력: {"path": "...", "content": "..."}
    """
    
    name: str = "file_write"
    description: str = "Write contents to a file"
    
    def __init__(self, base_dir: str = None):
        self._base_dir = Path(base_dir) if base_dir else Path.cwd()
    
    def run(self, path: str, content: str, **kwargs) -> ToolResult:
        """
        파일 쓰기
        
        Args:
            path: 파일 경로
            content: 작성할 내용
            
        Returns:
            ToolResult
        """
        start_time = time.time()
        encoding = kwargs.get("encoding", "utf-8")
        append = kwargs.get("append", False)
        
        try:
            file_path = self._resolve_path(path)
            
            # 디렉토리 자동 생성
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            mode = "a" if append else "w"
            with open(file_path, mode, encoding=encoding) as f:
                f.write(content)
            
            latency_ms = int((time.time() - start_time) * 1000)
            action = "appended" if append else "written"
            
            logger.info(f"[FileWrite] {path} | {len(content)} chars | {latency_ms}ms")
            
            return make_result(
                ok=True,
                output=f"Successfully {action} {len(content)} characters to {path}",
                error=None,
                latency_ms=latency_ms,
                tool_name=self.name,
                bytes_written=len(content.encode(encoding)),
            )
            
        except PermissionError:
            return make_result(
                ok=False,
                output=None,
                error=f"Permission denied: {path}",
                latency_ms=int((time.time() - start_time) * 1000),
                tool_name=self.name,
            )
            
        except Exception as e:
            logger.error(f"[FileWrite] Error: {e}")
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
