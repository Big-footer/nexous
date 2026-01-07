"""
DesktopCommanderTool - 시스템 명령 실행 Tool

이 파일의 책임:
- 안전한 시스템 명령 실행
- 명령어 화이트리스트/블랙리스트 관리
- 출력 캡처 및 처리
- 샌드박스 환경 제공
"""

from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field
import asyncio
import shlex
import os

from prometheus.tools.base import (
    BaseTool,
    ToolSchema,
    ToolParameter,
    ToolParameterType,
    ToolResult,
    ToolConfig,
)


class CommandSecurityLevel(str, Enum):
    """명령 보안 수준"""
    
    RESTRICTED = "restricted"  # 화이트리스트만
    NORMAL = "normal"          # 블랙리스트 제외
    PRIVILEGED = "privileged"  # 거의 모든 명령 허용


class CommandResult(BaseModel):
    """명령 실행 결과"""
    
    command: str
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    execution_time: float = 0.0
    success: bool = True


class DesktopCommanderConfig(ToolConfig):
    """Desktop Commander 설정"""
    
    timeout: float = 30.0
    max_output_length: int = 50000
    security_level: CommandSecurityLevel = CommandSecurityLevel.NORMAL
    working_directory: Optional[str] = None
    environment: Dict[str, str] = Field(default_factory=dict)
    
    # 화이트리스트 (RESTRICTED 모드)
    allowed_commands: List[str] = Field(default_factory=lambda: [
        "ls", "cat", "head", "tail", "grep", "find", "echo",
        "pwd", "date", "whoami", "wc", "sort", "uniq",
        "python", "python3", "pip", "pip3",
        "node", "npm", "npx",
        "git", "curl", "wget",
    ])
    
    # 블랙리스트 (NORMAL 모드)
    blocked_commands: List[str] = Field(default_factory=lambda: [
        "rm", "rmdir", "del", "format", "fdisk", "mkfs",
        "dd", "shutdown", "reboot", "halt", "poweroff",
        "passwd", "sudo", "su", "chown", "chmod",
        "kill", "killall", "pkill",
        "nc", "netcat", "nmap",
        ">", ">>", "|",  # 리다이렉션 (기본 차단)
    ])
    
    # 블랙리스트 경로
    blocked_paths: List[str] = Field(default_factory=lambda: [
        "/etc", "/bin", "/sbin", "/usr/bin", "/usr/sbin",
        "/root", "/var", "/boot", "/sys", "/proc",
        "C:\\Windows", "C:\\Program Files",
    ])


class DesktopCommanderTool(BaseTool):
    """
    시스템 명령 실행 Tool
    
    안전한 환경에서 시스템 명령을 실행합니다.
    보안 수준에 따른 명령어 제한이 적용됩니다.
    """
    
    name: str = "desktop_commander"
    description: str = "Execute system commands safely with security restrictions"
    
    def __init__(
        self,
        config: Optional[DesktopCommanderConfig] = None,
    ) -> None:
        """
        DesktopCommanderTool 초기화
        
        Args:
            config: 설정
        """
        super().__init__(config=config or DesktopCommanderConfig())
    
    def get_schema(self) -> ToolSchema:
        """Tool 스키마"""
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="command",
                    type=ToolParameterType.STRING,
                    description="Command to execute",
                    required=True,
                ),
                ToolParameter(
                    name="working_directory",
                    type=ToolParameterType.STRING,
                    description="Working directory for the command",
                    required=False,
                ),
                ToolParameter(
                    name="timeout",
                    type=ToolParameterType.NUMBER,
                    description="Timeout in seconds",
                    required=False,
                    default=30.0,
                ),
            ],
            returns="CommandResult with stdout, stderr, and return code",
            examples=[
                {"command": "ls -la"},
                {"command": "python --version"},
                {"command": "echo 'Hello World'"},
            ],
        )
    
    async def execute(
        self,
        command: str,
        working_directory: Optional[str] = None,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> ToolResult:
        """
        명령 실행
        
        Args:
            command: 실행할 명령
            working_directory: 작업 디렉토리
            timeout: 타임아웃 (초)
            
        Returns:
            실행 결과
        """
        import time
        start_time = time.time()
        
        # 보안 검증
        security_error = self._validate_command(command)
        if security_error:
            return ToolResult.error_result(security_error)
        
        # 작업 디렉토리 검증
        cwd = working_directory or self.config.working_directory
        if cwd and not self._validate_path(cwd):
            return ToolResult.error_result(f"Access denied to directory: {cwd}")
        
        # 타임아웃 설정
        cmd_timeout = timeout or self.config.timeout
        
        try:
            result = await self._run_command(
                command=command,
                cwd=cwd,
                timeout=cmd_timeout,
            )
            
            result.execution_time = time.time() - start_time
            
            if result.success:
                return ToolResult.success_result(
                    output=result.model_dump(),
                    execution_time=result.execution_time,
                )
            else:
                return ToolResult.error_result(
                    error=f"Command failed with code {result.return_code}: {result.stderr}",
                    execution_time=result.execution_time,
                    metadata={"stdout": result.stdout},
                )
                
        except asyncio.TimeoutError:
            return ToolResult.error_result(
                error=f"Command timeout after {cmd_timeout} seconds",
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            return ToolResult.error_result(
                error=str(e),
                execution_time=time.time() - start_time,
            )
    
    async def _run_command(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: float = 30.0,
    ) -> CommandResult:
        """
        명령 실행 (내부)
        
        Args:
            command: 명령
            cwd: 작업 디렉토리
            timeout: 타임아웃
            
        Returns:
            실행 결과
        """
        # 환경 변수 설정
        env = os.environ.copy()
        env.update(self.config.environment)
        
        # 프로세스 실행
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env,
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
            
            return CommandResult(
                command=command,
                stdout=self._truncate_output(stdout.decode('utf-8', errors='replace')),
                stderr=self._truncate_output(stderr.decode('utf-8', errors='replace')),
                return_code=process.returncode or 0,
                success=process.returncode == 0,
            )
            
        except asyncio.TimeoutError:
            process.kill()
            raise
    
    def _validate_command(
        self,
        command: str,
    ) -> Optional[str]:
        """
        명령 보안 검증
        
        Args:
            command: 검증할 명령
            
        Returns:
            오류 메시지 또는 None
        """
        # 명령 파싱
        try:
            parts = shlex.split(command)
        except ValueError:
            return "Invalid command syntax"
        
        if not parts:
            return "Empty command"
        
        base_command = parts[0]
        # 경로에서 명령어만 추출
        if '/' in base_command or '\\' in base_command:
            base_command = os.path.basename(base_command)
        
        security_level = self.config.security_level
        
        # RESTRICTED: 화이트리스트만
        if security_level == CommandSecurityLevel.RESTRICTED:
            if base_command not in self.config.allowed_commands:
                return f"Command not allowed: {base_command}"
        
        # NORMAL: 블랙리스트 제외
        elif security_level == CommandSecurityLevel.NORMAL:
            if base_command in self.config.blocked_commands:
                return f"Command blocked: {base_command}"
            
            # 위험 패턴 검사
            dangerous_patterns = [
                "$(", "`",  # 명령 치환
                "&&", "||",  # 명령 연결 (일부)
                "; ",  # 명령 구분
            ]
            for pattern in dangerous_patterns:
                if pattern in command:
                    return f"Dangerous pattern detected: {pattern}"
        
        # PRIVILEGED: 거의 허용 (여전히 일부 제한)
        elif security_level == CommandSecurityLevel.PRIVILEGED:
            critical_blocked = ["rm -rf /", "format", "fdisk", "mkfs"]
            for blocked in critical_blocked:
                if blocked in command:
                    return f"Critical command blocked: {blocked}"
        
        # 경로 검증 (인자에 경로가 있는 경우)
        for part in parts[1:]:
            if part.startswith('/') or part.startswith('C:\\'):
                if not self._validate_path(part):
                    return f"Access denied to path: {part}"
        
        return None
    
    def _validate_path(
        self,
        path: str,
    ) -> bool:
        """
        경로 검증
        
        Args:
            path: 검증할 경로
            
        Returns:
            허용 여부
        """
        # 절대 경로로 변환
        abs_path = os.path.abspath(path)
        
        # 블랙리스트 경로 검사
        for blocked in self.config.blocked_paths:
            if abs_path.startswith(blocked):
                return False
        
        return True
    
    def _truncate_output(
        self,
        output: str,
    ) -> str:
        """출력 길이 제한"""
        max_length = self.config.max_output_length
        if len(output) > max_length:
            return output[:max_length] + f"\n... (truncated, {len(output)} chars total)"
        return output
    
    async def run_script(
        self,
        script_path: str,
        args: Optional[List[str]] = None,
    ) -> ToolResult:
        """
        스크립트 실행
        
        Args:
            script_path: 스크립트 경로
            args: 인자 목록
            
        Returns:
            실행 결과
        """
        if not self._validate_path(script_path):
            return ToolResult.error_result(f"Access denied: {script_path}")
        
        if not os.path.exists(script_path):
            return ToolResult.error_result(f"Script not found: {script_path}")
        
        # 스크립트 유형 판단
        ext = os.path.splitext(script_path)[1].lower()
        
        if ext == '.py':
            command = f"python3 {shlex.quote(script_path)}"
        elif ext == '.sh':
            command = f"bash {shlex.quote(script_path)}"
        elif ext == '.js':
            command = f"node {shlex.quote(script_path)}"
        else:
            command = shlex.quote(script_path)
        
        # 인자 추가
        if args:
            command += " " + " ".join(shlex.quote(arg) for arg in args)
        
        return await self.execute(command)
    
    async def list_directory(
        self,
        path: str = ".",
        show_hidden: bool = False,
    ) -> ToolResult:
        """
        디렉토리 목록 조회
        
        Args:
            path: 디렉토리 경로
            show_hidden: 숨김 파일 표시 여부
            
        Returns:
            디렉토리 목록
        """
        flags = "-la" if show_hidden else "-l"
        return await self.execute(f"ls {flags} {shlex.quote(path)}")
    
    async def read_file(
        self,
        path: str,
        lines: Optional[int] = None,
    ) -> ToolResult:
        """
        파일 읽기
        
        Args:
            path: 파일 경로
            lines: 읽을 라인 수 (None이면 전체)
            
        Returns:
            파일 내용
        """
        if not self._validate_path(path):
            return ToolResult.error_result(f"Access denied: {path}")
        
        if lines:
            command = f"head -n {lines} {shlex.quote(path)}"
        else:
            command = f"cat {shlex.quote(path)}"
        
        return await self.execute(command)
    
    async def search_files(
        self,
        pattern: str,
        path: str = ".",
        file_type: Optional[str] = None,
    ) -> ToolResult:
        """
        파일 검색
        
        Args:
            pattern: 검색 패턴
            path: 검색 경로
            file_type: 파일 타입 (f: 파일, d: 디렉토리)
            
        Returns:
            검색 결과
        """
        command = f"find {shlex.quote(path)} -name {shlex.quote(pattern)}"
        if file_type:
            command += f" -type {file_type}"
        
        return await self.execute(command)
    
    async def grep(
        self,
        pattern: str,
        path: str,
        recursive: bool = False,
        ignore_case: bool = False,
    ) -> ToolResult:
        """
        텍스트 검색
        
        Args:
            pattern: 검색 패턴
            path: 검색 경로
            recursive: 재귀 검색
            ignore_case: 대소문자 무시
            
        Returns:
            검색 결과
        """
        flags = ""
        if recursive:
            flags += "r"
        if ignore_case:
            flags += "i"
        
        if flags:
            flags = f"-{flags}"
        
        command = f"grep {flags} {shlex.quote(pattern)} {shlex.quote(path)}"
        return await self.execute(command)
    
    def add_allowed_command(
        self,
        command: str,
    ) -> None:
        """허용 명령 추가"""
        if command not in self.config.allowed_commands:
            self.config.allowed_commands.append(command)
    
    def add_blocked_command(
        self,
        command: str,
    ) -> None:
        """차단 명령 추가"""
        if command not in self.config.blocked_commands:
            self.config.blocked_commands.append(command)
    
    def set_security_level(
        self,
        level: CommandSecurityLevel,
    ) -> None:
        """보안 수준 설정"""
        self.config.security_level = level
