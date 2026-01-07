"""
PROMETHEUS Secure Python Executor

Docker 기반 샌드박스에서 Python 코드를 안전하게 실행합니다.
"""

import subprocess
import tempfile
import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ExecutionMode(str, Enum):
    """실행 모드"""
    DOCKER = "docker"       # Docker 샌드박스 (가장 안전)
    RESTRICTED = "restricted"  # 제한된 exec (Docker 없을 때)
    UNSAFE = "unsafe"       # 무제한 exec (개발/테스트용, 위험!)


@dataclass
class ExecutionConfig:
    """실행 설정"""
    mode: ExecutionMode = ExecutionMode.DOCKER
    timeout: int = 30  # 초
    max_memory: str = "256m"  # Docker 메모리 제한
    network_enabled: bool = False  # 네트워크 허용 여부
    allowed_imports: set = None  # 허용된 import (RESTRICTED 모드)
    work_dir: str = "/tmp/prometheus_exec"  # 작업 디렉토리
    
    def __post_init__(self):
        if self.allowed_imports is None:
            self.allowed_imports = {
                'math', 'random', 'datetime', 'json', 'csv',
                'collections', 'itertools', 'functools',
                're', 'string', 'textwrap',
                'statistics', 'decimal', 'fractions',
            }


class SecurePythonExecutor:
    """
    안전한 Python 코드 실행기
    
    Docker 샌드박스를 사용하여 신뢰할 수 없는 코드를 안전하게 실행합니다.
    Docker가 없으면 제한된 exec 모드로 폴백합니다.
    """
    
    # 위험한 패턴 (RESTRICTED 모드에서 차단)
    DANGEROUS_PATTERNS = [
        'import os', 'from os', 'import sys', 'from sys',
        'import subprocess', 'from subprocess',
        'import shutil', 'from shutil',
        '__import__', 'eval(', 'exec(',
        'open(', 'file(',
        'import socket', 'from socket',
        'import requests', 'from requests',
        'import urllib', 'from urllib',
        'import http', 'from http',
        'import ftplib', 'import smtplib',
        'import pickle', 'from pickle',
        'import marshal', 'from marshal',
        'globals()', 'locals()',
        'getattr(', 'setattr(', 'delattr(',
        '__builtins__', '__code__', '__class__',
        'compile(', 'breakpoint(',
    ]
    
    def __init__(self, config: Optional[ExecutionConfig] = None):
        self.config = config or ExecutionConfig()
        self._docker_available = self._check_docker()
        
        # Docker가 없으면 RESTRICTED 모드로 폴백
        if self.config.mode == ExecutionMode.DOCKER and not self._docker_available:
            logger.warning("⚠️ Docker를 찾을 수 없습니다. RESTRICTED 모드로 폴백합니다.")
            self.config.mode = ExecutionMode.RESTRICTED
        
        # 작업 디렉토리 생성
        Path(self.config.work_dir).mkdir(parents=True, exist_ok=True)
    
    def _check_docker(self) -> bool:
        """Docker 사용 가능 여부 확인"""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def execute(self, code: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Python 코드 실행
        
        Args:
            code: 실행할 Python 코드
            context: 전달할 변수 (선택)
        
        Returns:
            실행 결과 문자열
        """
        if self.config.mode == ExecutionMode.DOCKER:
            return self._execute_docker(code, context)
        elif self.config.mode == ExecutionMode.RESTRICTED:
            return self._execute_restricted(code, context)
        else:
            return self._execute_unsafe(code, context)
    
    def _execute_docker(self, code: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Docker 샌드박스에서 실행 (가장 안전)"""
        
        # 임시 파일 생성
        temp_dir = tempfile.mkdtemp(dir=self.config.work_dir)
        script_path = os.path.join(temp_dir, "script.py")
        
        try:
            # 코드 파일 작성
            full_code = self._prepare_code(code, context)
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(full_code)
            
            # Docker 명령어 구성
            docker_cmd = [
                "docker", "run",
                "--rm",  # 실행 후 컨테이너 삭제
                "--memory", self.config.max_memory,  # 메모리 제한
                "--cpus", "0.5",  # CPU 제한
                "--pids-limit", "50",  # 프로세스 수 제한
                "--read-only",  # 읽기 전용 파일시스템
                "--tmpfs", "/tmp:size=50m",  # 임시 쓰기 공간
                "-v", f"{script_path}:/app/script.py:ro",  # 스크립트 마운트 (읽기 전용)
            ]
            
            # 네트워크 설정
            if not self.config.network_enabled:
                docker_cmd.extend(["--network", "none"])
            
            # Python 이미지 및 실행 명령
            docker_cmd.extend([
                "python:3.11-slim",
                "python", "-u", "/app/script.py"
            ])
            
            # 실행
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout
            )
            
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            
            if result.returncode == 0:
                return stdout if stdout else "실행 완료 (출력 없음)"
            else:
                return f"❌ 오류 (exit code {result.returncode}):\n{stderr or stdout}"
        
        except subprocess.TimeoutExpired:
            return f"❌ 실행 시간 초과 ({self.config.timeout}초)"
        
        except Exception as e:
            return f"❌ Docker 실행 오류: {str(e)}"
        
        finally:
            # 임시 파일 정리
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _execute_restricted(self, code: str, context: Optional[Dict[str, Any]] = None) -> str:
        """제한된 환경에서 실행 (Docker 없을 때)"""
        
        # 위험한 패턴 검사
        code_lower = code.lower()
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern.lower() in code_lower:
                return f"❌ 보안 위반: '{pattern}' 패턴이 감지되었습니다."
        
        # 안전한 builtins만 허용
        safe_builtins = {
            'abs': abs, 'all': all, 'any': any, 'ascii': ascii,
            'bin': bin, 'bool': bool, 'bytearray': bytearray, 'bytes': bytes,
            'callable': callable, 'chr': chr, 'complex': complex,
            'dict': dict, 'divmod': divmod, 'enumerate': enumerate,
            'filter': filter, 'float': float, 'format': format,
            'frozenset': frozenset, 'hash': hash, 'hex': hex,
            'int': int, 'isinstance': isinstance, 'issubclass': issubclass,
            'iter': iter, 'len': len, 'list': list, 'map': map,
            'max': max, 'min': min, 'next': next, 'oct': oct,
            'ord': ord, 'pow': pow, 'print': print, 'range': range,
            'repr': repr, 'reversed': reversed, 'round': round,
            'set': set, 'slice': slice, 'sorted': sorted,
            'str': str, 'sum': sum, 'tuple': tuple, 'type': type,
            'zip': zip,
            'True': True, 'False': False, 'None': None,
        }
        
        # 허용된 모듈만 import 가능하게 설정
        import importlib
        
        def safe_import(name, *args, **kwargs):
            if name in self.config.allowed_imports:
                return importlib.import_module(name)
            raise ImportError(f"모듈 '{name}'은(는) 보안상 import할 수 없습니다.")
        
        safe_builtins['__import__'] = safe_import
        
        # 실행 환경 구성
        exec_globals = {'__builtins__': safe_builtins}
        
        if context:
            exec_globals.update(context)
        
        # stdout 캡처
        import io
        from contextlib import redirect_stdout, redirect_stderr
        
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, exec_globals)
            
            output = stdout_capture.getvalue()
            errors = stderr_capture.getvalue()
            
            if errors:
                return f"Output:\n{output}\n\nWarnings:\n{errors}"
            return output if output else "실행 완료 (출력 없음)"
        
        except Exception as e:
            return f"❌ 실행 오류: {str(e)}"
    
    def _execute_unsafe(self, code: str, context: Optional[Dict[str, Any]] = None) -> str:
        """무제한 실행 (개발용, 매우 위험!)"""
        logger.warning("⚠️ UNSAFE 모드로 코드를 실행합니다. 프로덕션에서 사용하지 마세요!")
        
        import io
        from contextlib import redirect_stdout, redirect_stderr
        
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        exec_globals = {'__builtins__': __builtins__}
        if context:
            exec_globals.update(context)
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, exec_globals)
            
            output = stdout_capture.getvalue()
            errors = stderr_capture.getvalue()
            
            if errors:
                return f"Output:\n{output}\n\nWarnings/Errors:\n{errors}"
            return output if output else "실행 완료 (출력 없음)"
        
        except Exception as e:
            return f"❌ 오류: {str(e)}"
    
    def _prepare_code(self, code: str, context: Optional[Dict[str, Any]] = None) -> str:
        """실행할 코드 준비"""
        lines = []
        
        # context 변수 주입
        if context:
            lines.append("# Context variables")
            for key, value in context.items():
                lines.append(f"{key} = {repr(value)}")
            lines.append("")
        
        # 사용자 코드
        lines.append("# User code")
        lines.append(code)
        
        return "\n".join(lines)


# =============================================================================
# 전역 실행기 인스턴스
# =============================================================================

# 기본 실행기 (Docker 우선, 없으면 RESTRICTED)
_default_executor: Optional[SecurePythonExecutor] = None


def get_executor(mode: Optional[ExecutionMode] = None) -> SecurePythonExecutor:
    """실행기 인스턴스 반환"""
    global _default_executor
    
    if mode:
        return SecurePythonExecutor(ExecutionConfig(mode=mode))
    
    if _default_executor is None:
        _default_executor = SecurePythonExecutor()
    
    return _default_executor


def secure_python_exec(code: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    안전한 Python 코드 실행 (간편 함수)
    
    Args:
        code: 실행할 Python 코드
        context: 전달할 변수 (선택)
    
    Returns:
        실행 결과 문자열
    """
    executor = get_executor()
    return executor.execute(code, context)
