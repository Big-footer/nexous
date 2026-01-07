"""
NEXOUS Test - Tool 실행 Trace 검증

Tool 3개(python_exec, file_read, file_write) 실행 및 trace 기록 검증
"""

import os
import json
import pytest
from pathlib import Path


class TestToolRegistry:
    """Tool Registry 테스트"""
    
    def test_registry_singleton(self):
        """Registry 싱글톤 검증"""
        from nexous.tools import get_registry
        
        reg1 = get_registry()
        reg2 = get_registry()
        
        assert reg1 is reg2
    
    def test_registry_list_tools(self):
        """등록된 Tool 목록 검증"""
        from nexous.tools import get_registry, ALLOWED_TOOLS
        
        registry = get_registry()
        tools = registry.list_tools()
        
        assert tools == ALLOWED_TOOLS
        assert "python_exec" in tools
        assert "file_read" in tools
        assert "file_write" in tools
        assert len(tools) == 3
    
    def test_registry_get_tool(self):
        """Tool 인스턴스 반환 검증"""
        from nexous.tools import get_registry
        
        registry = get_registry()
        
        tool = registry.get("python_exec")
        assert tool.name == "python_exec"
        
        tool = registry.get("file_read")
        assert tool.name == "file_read"
        
        tool = registry.get("file_write")
        assert tool.name == "file_write"
    
    def test_registry_disallowed_tool(self):
        """허용되지 않은 Tool 요청 시 에러"""
        from nexous.tools import get_registry, ToolError
        
        registry = get_registry()
        
        with pytest.raises(ToolError):
            registry.get("shell_exec")


class TestPythonExecTool:
    """python_exec Tool 테스트"""
    
    def test_python_exec_success(self):
        """python_exec 성공 케이스"""
        from nexous.tools import get_registry
        
        tool = get_registry().get("python_exec")
        result = tool.run(code="print(1+2+3)")
        
        assert result["ok"] is True
        assert result["output"] == "6"
        assert result["error"] is None
        assert "latency_ms" in result["metadata"]
    
    def test_python_exec_syntax_error(self):
        """python_exec 문법 에러"""
        from nexous.tools import get_registry
        
        tool = get_registry().get("python_exec")
        result = tool.run(code="print(")
        
        assert result["ok"] is False
        assert result["output"] is None
        assert "SyntaxError" in result["error"]
    
    def test_python_exec_runtime_error(self):
        """python_exec 런타임 에러"""
        from nexous.tools import get_registry
        
        tool = get_registry().get("python_exec")
        result = tool.run(code="print(undefined_var)")
        
        assert result["ok"] is False
        assert "NameError" in result["error"]
    
    def test_python_exec_allowed_modules(self):
        """python_exec 허용 모듈"""
        from nexous.tools import get_registry
        
        tool = get_registry().get("python_exec")
        result = tool.run(code="import math; print(math.pi)")
        
        assert result["ok"] is True
        assert "3.14" in result["output"]
    
    def test_python_exec_disallowed_modules(self):
        """python_exec 비허용 모듈"""
        from nexous.tools import get_registry
        
        tool = get_registry().get("python_exec")
        result = tool.run(code="import os; print(os.getcwd())")
        
        assert result["ok"] is False
        assert "ImportError" in result["error"]


class TestFileReadTool:
    """file_read Tool 테스트"""
    
    def test_file_read_success(self, tmp_path):
        """file_read 성공 케이스"""
        from nexous.tools import get_registry
        from nexous.tools.file_read import FileReadTool
        
        # 테스트 파일 생성
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")
        
        tool = FileReadTool(base_dir=str(tmp_path))
        result = tool.run(path="test.txt")
        
        assert result["ok"] is True
        assert result["output"] == "Hello World"
    
    def test_file_read_not_found(self, tmp_path):
        """file_read 파일 없음"""
        from nexous.tools.file_read import FileReadTool
        
        tool = FileReadTool(base_dir=str(tmp_path))
        result = tool.run(path="nonexistent.txt")
        
        assert result["ok"] is False
        assert "not found" in result["error"].lower()


class TestFileWriteTool:
    """file_write Tool 테스트"""
    
    def test_file_write_success(self, tmp_path):
        """file_write 성공 케이스"""
        from nexous.tools.file_write import FileWriteTool
        
        tool = FileWriteTool(base_dir=str(tmp_path))
        result = tool.run(path="output.txt", content="Test Content")
        
        assert result["ok"] is True
        assert "Successfully" in result["output"]
        
        # 실제 파일 확인
        written_file = tmp_path / "output.txt"
        assert written_file.exists()
        assert written_file.read_text() == "Test Content"
    
    def test_file_write_creates_directory(self, tmp_path):
        """file_write 디렉토리 자동 생성"""
        from nexous.tools.file_write import FileWriteTool
        
        tool = FileWriteTool(base_dir=str(tmp_path))
        result = tool.run(path="subdir/nested/file.txt", content="Nested")
        
        assert result["ok"] is True
        
        nested_file = tmp_path / "subdir" / "nested" / "file.txt"
        assert nested_file.exists()


class TestToolTraceRecording:
    """Tool 호출 Trace 기록 검증"""
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY", "").startswith("sk-"),
        reason="OPENAI_API_KEY not set"
    )
    def test_tool_call_recorded_in_trace(self, test_trace_dir):
        """Tool 호출이 trace에 기록되는지 검증"""
        from nexous.core import TraceWriter, GenericAgent
        
        trace = TraceWriter(base_dir=str(test_trace_dir))
        trace.start_run("tool_test", "tool_trace", "sequential")
        trace.start_agent("calc_agent", "calculator", "계산")
        
        agent = GenericAgent(
            agent_id="calc_agent",
            role="calculator",
            purpose="Python 계산",
            llm_config={"provider": "openai", "model": "gpt-4o"},
            tools=["python_exec"],
            system_prompt="반드시 Python 코드로 계산하고 print()로 출력하세요.",
            trace_callback=trace.log_step,
        )
        
        agent.execute({"inputs": {"task": "2+3을 계산하세요"}})
        
        trace.end_agent("calc_agent", "COMPLETED")
        trace.end_run("COMPLETED")
        
        # Trace 검증
        trace_path = test_trace_dir / "tool_test" / "tool_trace" / "trace.json"
        with open(trace_path) as f:
            trace_data = json.load(f)
        
        assert trace_data["status"] == "COMPLETED"
        assert trace_data["summary"]["total_tool_calls"] >= 1
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY", "").startswith("sk-"),
        reason="OPENAI_API_KEY not set"
    )
    def test_tool_trace_contains_tool_name(self, test_trace_dir):
        """Tool trace에 tool_name 포함 검증"""
        from nexous.core import TraceWriter, GenericAgent
        
        trace = TraceWriter(base_dir=str(test_trace_dir))
        trace.start_run("tool_name_test", "name_trace", "sequential")
        trace.start_agent("agent1", "calc", "계산")
        
        agent = GenericAgent(
            agent_id="agent1",
            role="calc",
            purpose="계산",
            llm_config={"provider": "openai", "model": "gpt-4o"},
            tools=["python_exec"],
            system_prompt="Python 코드로 계산하고 print()로 출력하세요.",
            trace_callback=trace.log_step,
        )
        
        agent.execute({"inputs": {"task": "1*2*3 계산"}})
        
        trace.end_agent("agent1", "COMPLETED")
        trace.end_run("COMPLETED")
        
        # Trace 검증
        trace_path = test_trace_dir / "tool_name_test" / "name_trace" / "trace.json"
        with open(trace_path) as f:
            trace_data = json.load(f)
        
        # TOOL step 찾기
        tool_steps = []
        for agent in trace_data["agents"]:
            for step in agent["steps"]:
                if step["type"] == "TOOL":
                    tool_steps.append(step)
        
        if tool_steps:
            assert tool_steps[0]["tool_name"] == "python_exec"
