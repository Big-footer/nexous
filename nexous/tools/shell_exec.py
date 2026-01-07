"""
NEXOUS Tool - Shell Exec

Shell 명령 실행 도구
"""

from __future__ import annotations

import subprocess
import time
import logging
import shlex
from typing import Optional

from .base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class ShellExecTool(BaseTool):
    """
    Shell 명령 실행 도구
    
    제한된 명령만 허용
    """
    
    name = "shell_exec"
    description = "Execute shell commands"
    
    # 허용된 명령 (보안)
    ALLOWED_COMMANDS = {
        "ls", "cat", "head", "tail", "wc", "grep", "find",
        "echo", "date", "pwd", "mkdir", "cp", "mv",
        "python", "python3", "pip", "pip3",
    }
    
    # 금지된 패턴
    FORBIDDEN_PATTERNS = [
        "rm -rf", "sudo", "chmod 777", "|", "&&", ";",
        ">", ">>", "<", "$(", "`",
    ]
    
    TIMEOUT = 30  # seconds
    
    def execute(self, command: str, timeout: int = None) -> ToolResult:
        """
        Shell 명령 실행
        
        Args:
            command: 실행할 명령
            timeout: 타임아웃 (초)
            
        Returns:
            ToolResult
        """
        start_time = time.time()
        timeout = timeout or self.TIMEOUT
        
        # 보안 검증
        if not self._is_allowed(command):
            return ToolResult(
                success=False,
                output=None,
                error=f"Command not allowed: {command}",
                latency_ms=int((time.time() - start_time) * 1000)
            )
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=None
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            if result.returncode == 0:
                logger.info(f"[ShellExec] {command[:50]}... | {latency_ms}ms")
                return ToolResult(
                    success=True,
                    output=result.stdout.strip() or "(no output)",
                    latency_ms=latency_ms
                )
            else:
                logger.warning(f"[ShellExec] Command failed: {result.stderr}")
                return ToolResult(
                    success=False,
                    output=result.stdout.strip(),
                    error=result.stderr.strip(),
                    latency_ms=latency_ms
                )
                
        except subprocess.TimeoutExpired:
            latency_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                output=None,
                error=f"Command timed out after {timeout}s",
                latency_ms=latency_ms
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
                latency_ms=latency_ms
            )
    
    def _is_allowed(self, command: str) -> bool:
        """명령 허용 여부 확인"""
        # 금지 패턴 검사
        for pattern in self.FORBIDDEN_PATTERNS:
            if pattern in command:
                return False
        
        # 첫 번째 명령어 추출
        try:
            parts = shlex.split(command)
            if not parts:
                return False
            
            first_cmd = parts[0].split("/")[-1]
            return first_cmd in self.ALLOWED_COMMANDS
        except:
            return False
