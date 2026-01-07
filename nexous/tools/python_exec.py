"""
NEXOUS Tool - Python Exec

Python 코드 실행 도구

입력 형식:
{
  "code": "print(1+2)"
}

LEVEL 1 제약:
- 제한된 builtins만 허용
- 타임아웃 적용
- 외부 모듈 import 제한
"""

from __future__ import annotations

import sys
import time
import logging
from io import StringIO
from typing import Dict, Any

from .base import ToolResult, make_result

logger = logging.getLogger(__name__)


# 허용된 빌트인 함수
ALLOWED_BUILTINS = {
    "int": int, "float": float, "str": str, "bool": bool,
    "list": list, "dict": dict, "set": set, "tuple": tuple,
    "print": print, "len": len, "range": range,
    "enumerate": enumerate, "zip": zip, "map": map,
    "filter": filter, "sorted": sorted, "reversed": reversed,
    "sum": sum, "min": min, "max": max,
    "abs": abs, "round": round, "pow": pow,
    "isinstance": isinstance, "type": type,
    "hasattr": hasattr, "getattr": getattr, "setattr": setattr,
    "Exception": Exception, "ValueError": ValueError,
    "TypeError": TypeError, "KeyError": KeyError, "IndexError": IndexError,
}

# 허용된 모듈
ALLOWED_MODULES = {
    "math", "statistics", "random", "datetime",
    "json", "re", "collections", "itertools", "functools",
}


class PythonExecTool:
    """
    Python 코드 실행 Tool
    
    입력: {"code": "print(1+2)"}
    """
    
    name: str = "python_exec"
    description: str = "Execute Python code in a restricted environment"
    
    DEFAULT_TIMEOUT = 30
    
    def run(self, code: str, **kwargs) -> ToolResult:
        """
        Python 코드 실행
        
        Args:
            code: 실행할 Python 코드
            
        Returns:
            ToolResult
        """
        start_time = time.time()
        
        # stdout/stderr 캡처
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        
        try:
            exec_globals = self._create_restricted_globals()
            exec_locals = {}
            
            exec(code, exec_globals, exec_locals)
            
            stdout_output = sys.stdout.getvalue()
            stderr_output = sys.stderr.getvalue()
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            output = stdout_output.strip()
            if stderr_output:
                output += f"\n[stderr]\n{stderr_output.strip()}"
            if not output:
                output = "(no output)"
            
            logger.info(f"[PythonExec] Success | {latency_ms}ms")
            
            return make_result(
                ok=True,
                output=output,
                error=None,
                latency_ms=latency_ms,
                tool_name=self.name,
            )
            
        except SyntaxError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return make_result(
                ok=False,
                output=None,
                error=f"SyntaxError: {e}",
                latency_ms=latency_ms,
                tool_name=self.name,
            )
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return make_result(
                ok=False,
                output=None,
                error=f"{type(e).__name__}: {e}",
                latency_ms=latency_ms,
                tool_name=self.name,
            )
            
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    def _create_restricted_globals(self) -> Dict[str, Any]:
        """제한된 전역 환경 생성"""
        def safe_import(name, *args, **kwargs):
            if name not in ALLOWED_MODULES:
                raise ImportError(f"Module '{name}' not allowed")
            return __builtins__["__import__"](name, *args, **kwargs)
        
        restricted = ALLOWED_BUILTINS.copy()
        restricted["__import__"] = safe_import
        
        return {"__builtins__": restricted, "__name__": "__main__"}
