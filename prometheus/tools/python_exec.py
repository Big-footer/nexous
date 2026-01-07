"""
PythonExecTool - Python 코드 실행 Tool

이 파일의 책임:
- Python 코드 안전 실행
- 샌드박스 환경 제공
- 실행 결과 캡처
- 타임아웃 관리
"""

from typing import Any, Dict, List, Optional
import sys
import io
import ast
import traceback
import asyncio
from contextlib import redirect_stdout, redirect_stderr
from pydantic import BaseModel, Field

from prometheus.tools.base import (
    BaseTool,
    ToolSchema,
    ToolParameter,
    ToolParameterType,
    ToolResult,
    ToolConfig,
)


class PythonExecConfig(ToolConfig):
    """Python 실행 Tool 설정"""
    
    timeout: float = 30.0
    max_output_length: int = 10000
    allowed_imports: Optional[List[str]] = None
    blocked_imports: List[str] = Field(default_factory=lambda: [
        "os", "subprocess", "shutil", "sys", "socket",
        "requests", "urllib", "http", "ftplib",
    ])
    allow_file_access: bool = False
    max_memory_mb: int = 512


class ExecutionResult(BaseModel):
    """실행 결과"""
    
    stdout: str = ""
    stderr: str = ""
    return_value: Any = None
    variables: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    execution_time: float = 0.0


class PythonExecTool(BaseTool):
    """
    Python 코드 실행 Tool
    
    Python 코드를 안전한 샌드박스 환경에서 실행합니다.
    위험한 작업을 방지하기 위한 제한이 적용됩니다.
    """
    
    name: str = "python_exec"
    description: str = "Execute Python code in a sandboxed environment"
    
    # 안전한 내장 함수 목록
    SAFE_BUILTINS = {
        'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytearray', 'bytes',
        'callable', 'chr', 'complex', 'dict', 'dir', 'divmod', 'enumerate',
        'filter', 'float', 'format', 'frozenset', 'getattr', 'hasattr', 'hash',
        'hex', 'int', 'isinstance', 'issubclass', 'iter', 'len', 'list',
        'map', 'max', 'min', 'next', 'object', 'oct', 'ord', 'pow', 'print',
        'range', 'repr', 'reversed', 'round', 'set', 'slice', 'sorted',
        'str', 'sum', 'tuple', 'type', 'zip',
        'True', 'False', 'None',
    }
    
    def __init__(
        self,
        config: Optional[PythonExecConfig] = None,
    ) -> None:
        """
        PythonExecTool 초기화
        
        Args:
            config: 설정
        """
        super().__init__(config=config or PythonExecConfig())
        self._safe_globals = self._create_safe_globals()
    
    def get_schema(self) -> ToolSchema:
        """Tool 스키마"""
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="code",
                    type=ToolParameterType.STRING,
                    description="Python code to execute",
                    required=True,
                ),
                ToolParameter(
                    name="variables",
                    type=ToolParameterType.OBJECT,
                    description="Variables to inject into execution context",
                    required=False,
                    default={},
                ),
            ],
            returns="ExecutionResult with stdout, stderr, return_value, variables",
            examples=[
                {
                    "code": "result = 2 + 2\nprint(result)",
                    "variables": {},
                },
                {
                    "code": "squares = [x**2 for x in range(10)]\nprint(squares)",
                    "variables": {},
                },
            ],
        )
    
    async def execute(
        self,
        code: str,
        variables: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> ToolResult:
        """
        Python 코드 실행
        
        Args:
            code: 실행할 Python 코드
            variables: 주입할 변수
            
        Returns:
            실행 결과
        """
        import time
        start_time = time.time()
        
        # 코드 검증
        validation_error = self._validate_code(code)
        if validation_error:
            return ToolResult.error_result(validation_error)
        
        # 실행 환경 준비
        exec_globals = self._safe_globals.copy()
        if variables:
            exec_globals.update(variables)
        
        # 출력 캡처
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        result = ExecutionResult()
        
        try:
            # 타임아웃과 함께 실행
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec_result = await asyncio.wait_for(
                    self._run_code(code, exec_globals),
                    timeout=self.config.timeout,
                )
            
            result.stdout = self._truncate_output(stdout_capture.getvalue())
            result.stderr = self._truncate_output(stderr_capture.getvalue())
            result.return_value = exec_result
            
            # 새로 생성된 변수 추출
            result.variables = {
                k: v for k, v in exec_globals.items()
                if k not in self._safe_globals and not k.startswith('_')
            }
            
        except asyncio.TimeoutError:
            result.error = f"Execution timeout after {self.config.timeout} seconds"
            result.stdout = self._truncate_output(stdout_capture.getvalue())
            result.stderr = self._truncate_output(stderr_capture.getvalue())
            
        except Exception as e:
            result.error = f"{type(e).__name__}: {str(e)}"
            result.stderr = traceback.format_exc()
        
        result.execution_time = time.time() - start_time
        
        if result.error:
            return ToolResult.error_result(
                error=result.error,
                execution_time=result.execution_time,
                metadata={"stdout": result.stdout, "stderr": result.stderr},
            )
        
        return ToolResult.success_result(
            output=result.model_dump(),
            execution_time=result.execution_time,
        )
    
    async def _run_code(
        self,
        code: str,
        globals_dict: Dict[str, Any],
    ) -> Any:
        """
        코드 실행 (비동기 래퍼)
        
        Args:
            code: 코드
            globals_dict: 전역 변수
            
        Returns:
            실행 결과
        """
        # exec는 동기 함수이므로 executor에서 실행
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._execute_sync,
            code,
            globals_dict,
        )
    
    def _execute_sync(
        self,
        code: str,
        globals_dict: Dict[str, Any],
    ) -> Any:
        """
        동기 코드 실행
        
        Args:
            code: 코드
            globals_dict: 전역 변수
            
        Returns:
            마지막 표현식의 값
        """
        # 코드 파싱
        tree = ast.parse(code)
        
        # 마지막이 표현식이면 반환값으로 처리
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            last_expr = tree.body.pop()
            exec(compile(tree, '<string>', 'exec'), globals_dict)
            return eval(compile(ast.Expression(last_expr.value), '<string>', 'eval'), globals_dict)
        else:
            exec(compile(tree, '<string>', 'exec'), globals_dict)
            return None
    
    def _validate_code(self, code: str) -> Optional[str]:
        """
        코드 검증
        
        Args:
            code: 검증할 코드
            
        Returns:
            오류 메시지 또는 None
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return f"Syntax error: {e}"
        
        # import 검증
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in getattr(node, 'names', []):
                    module_name = alias.name.split('.')[0]
                    
                    # blocked imports 검사
                    if module_name in self.config.blocked_imports:
                        return f"Import blocked: {module_name}"
                    
                    # allowed imports 검사 (설정된 경우)
                    if (self.config.allowed_imports is not None and 
                        module_name not in self.config.allowed_imports):
                        return f"Import not allowed: {module_name}"
            
            # 위험한 함수 호출 검사
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ['eval', 'exec', 'compile', '__import__', 'open']:
                        return f"Function not allowed: {node.func.id}"
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in ['system', 'popen', 'spawn']:
                        return f"Method not allowed: {node.func.attr}"
        
        return None
    
    def _create_safe_globals(self) -> Dict[str, Any]:
        """
        안전한 전역 변수 생성
        
        Returns:
            안전한 전역 변수 딕셔너리
        """
        import builtins
        
        safe_builtins = {
            name: getattr(builtins, name)
            for name in self.SAFE_BUILTINS
            if hasattr(builtins, name)
        }
        
        # 안전한 모듈 추가
        safe_globals = {
            '__builtins__': safe_builtins,
            '__name__': '__main__',
        }
        
        # math, json 등 안전한 모듈 허용
        try:
            import math
            safe_globals['math'] = math
        except ImportError:
            pass
        
        try:
            import json
            safe_globals['json'] = json
        except ImportError:
            pass
        
        try:
            import datetime
            safe_globals['datetime'] = datetime
        except ImportError:
            pass
        
        try:
            import re
            safe_globals['re'] = re
        except ImportError:
            pass
        
        return safe_globals
    
    def _truncate_output(self, output: str) -> str:
        """
        출력 길이 제한
        
        Args:
            output: 원본 출력
            
        Returns:
            제한된 출력
        """
        max_length = self.config.max_output_length
        if len(output) > max_length:
            return output[:max_length] + f"\n... (truncated, {len(output)} chars total)"
        return output
    
    def add_allowed_module(self, module_name: str, module: Any) -> None:
        """
        허용 모듈 추가
        
        Args:
            module_name: 모듈 이름
            module: 모듈 객체
        """
        self._safe_globals[module_name] = module
    
    def remove_blocked_import(self, module_name: str) -> bool:
        """
        차단 목록에서 제거
        
        Args:
            module_name: 모듈 이름
            
        Returns:
            제거 성공 여부
        """
        if module_name in self.config.blocked_imports:
            self.config.blocked_imports.remove(module_name)
            return True
        return False
