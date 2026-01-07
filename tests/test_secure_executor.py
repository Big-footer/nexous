"""
Secure Python Executor 테스트
"""

import pytest
from prometheus.tools.secure_executor import (
    SecurePythonExecutor,
    ExecutionConfig,
    ExecutionMode,
    secure_python_exec,
    get_executor,
)


class TestSecurePythonExecutor:
    """SecurePythonExecutor 테스트"""
    
    def test_executor_initialization(self):
        """초기화 테스트"""
        executor = SecurePythonExecutor()
        assert executor is not None
        assert executor.config.timeout == 30
    
    def test_restricted_mode_basic(self):
        """RESTRICTED 모드 기본 테스트"""
        executor = SecurePythonExecutor(
            ExecutionConfig(mode=ExecutionMode.RESTRICTED)
        )
        
        result = executor.execute("print(1 + 1)")
        assert "2" in result
    
    def test_restricted_mode_math(self):
        """RESTRICTED 모드 math 모듈 테스트"""
        executor = SecurePythonExecutor(
            ExecutionConfig(mode=ExecutionMode.RESTRICTED)
        )
        
        code = """
import math
print(math.sqrt(16))
"""
        result = executor.execute(code)
        assert "4.0" in result
    
    def test_restricted_mode_blocks_os(self):
        """RESTRICTED 모드 os 차단 테스트"""
        executor = SecurePythonExecutor(
            ExecutionConfig(mode=ExecutionMode.RESTRICTED)
        )
        
        result = executor.execute("import os")
        assert "보안 위반" in result or "오류" in result
    
    def test_restricted_mode_blocks_subprocess(self):
        """RESTRICTED 모드 subprocess 차단 테스트"""
        executor = SecurePythonExecutor(
            ExecutionConfig(mode=ExecutionMode.RESTRICTED)
        )
        
        result = executor.execute("import subprocess")
        assert "보안 위반" in result or "오류" in result
    
    def test_restricted_mode_blocks_eval(self):
        """RESTRICTED 모드 eval 차단 테스트"""
        executor = SecurePythonExecutor(
            ExecutionConfig(mode=ExecutionMode.RESTRICTED)
        )
        
        result = executor.execute("eval('1+1')")
        assert "보안 위반" in result or "오류" in result
    
    def test_restricted_mode_blocks_open(self):
        """RESTRICTED 모드 open 차단 테스트"""
        executor = SecurePythonExecutor(
            ExecutionConfig(mode=ExecutionMode.RESTRICTED)
        )
        
        result = executor.execute("open('/etc/passwd', 'r')")
        assert "보안 위반" in result or "오류" in result
    
    def test_restricted_mode_blocks_exec(self):
        """RESTRICTED 모드 내부 exec 차단 테스트"""
        executor = SecurePythonExecutor(
            ExecutionConfig(mode=ExecutionMode.RESTRICTED)
        )
        
        result = executor.execute("exec('print(1)')")
        assert "보안 위반" in result or "오류" in result
    
    def test_restricted_mode_with_context(self):
        """RESTRICTED 모드 context 변수 테스트"""
        executor = SecurePythonExecutor(
            ExecutionConfig(mode=ExecutionMode.RESTRICTED)
        )
        
        result = executor.execute(
            "print(x + y)",
            context={"x": 10, "y": 20}
        )
        assert "30" in result
    
    def test_restricted_mode_allowed_imports(self):
        """RESTRICTED 모드 허용된 import 테스트"""
        executor = SecurePythonExecutor(
            ExecutionConfig(mode=ExecutionMode.RESTRICTED)
        )
        
        # json, datetime, collections 등은 허용됨
        code = """
import json
data = {"a": 1, "b": 2}
print(json.dumps(data))
"""
        result = executor.execute(code)
        assert '"a": 1' in result or '"a":1' in result


class TestSecurePythonExecFunction:
    """secure_python_exec 함수 테스트"""
    
    def test_simple_execution(self):
        """간단한 실행 테스트"""
        result = secure_python_exec("print('Hello, World!')")
        assert "Hello" in result
    
    def test_calculation(self):
        """계산 테스트"""
        result = secure_python_exec("print(sum(range(1, 11)))")
        assert "55" in result
    
    def test_loop(self):
        """반복문 테스트"""
        code = """
for i in range(5):
    print(i)
"""
        result = secure_python_exec(code)
        assert "0" in result
        assert "4" in result


class TestExecutionModes:
    """실행 모드 테스트"""
    
    def test_get_executor_default(self):
        """기본 executor 테스트"""
        executor = get_executor()
        assert executor is not None
    
    def test_get_executor_restricted(self):
        """RESTRICTED 모드 executor 테스트"""
        executor = get_executor(ExecutionMode.RESTRICTED)
        assert executor.config.mode == ExecutionMode.RESTRICTED
    
    def test_execution_config_defaults(self):
        """ExecutionConfig 기본값 테스트"""
        config = ExecutionConfig()
        assert config.timeout == 30
        assert config.max_memory == "256m"
        assert config.network_enabled == False
        assert "math" in config.allowed_imports
        assert "os" not in config.allowed_imports


class TestDockerExecution:
    """Docker 실행 테스트 (Docker 있을 때만)"""
    
    @pytest.fixture
    def docker_executor(self):
        """Docker executor fixture"""
        executor = SecurePythonExecutor(
            ExecutionConfig(mode=ExecutionMode.DOCKER)
        )
        if not executor._docker_available:
            pytest.skip("Docker not available")
        return executor
    
    def test_docker_simple(self, docker_executor):
        """Docker 간단한 실행"""
        result = docker_executor.execute("print('Hello from Docker!')")
        assert "Hello" in result or "Docker" in result
    
    def test_docker_calculation(self, docker_executor):
        """Docker 계산 테스트"""
        result = docker_executor.execute("print(2 ** 10)")
        assert "1024" in result
    
    def test_docker_no_network(self, docker_executor):
        """Docker 네트워크 차단 테스트"""
        code = """
import urllib.request
try:
    urllib.request.urlopen('http://google.com')
    print('Network OK')
except Exception as e:
    print(f'Network blocked: {e}')
"""
        result = docker_executor.execute(code)
        # 네트워크가 차단되어 있으면 에러가 발생해야 함
        assert "blocked" in result.lower() or "error" in result.lower() or "오류" in result
