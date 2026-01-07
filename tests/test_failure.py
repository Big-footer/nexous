"""
NEXOUS Test - 실패 케이스 검증

실패 시 trace.status=FAILED + error 기록 검증
"""

import os
import json
import pytest
from pathlib import Path


class TestFailureTrace:
    """실패 케이스 Trace 검증"""
    
    def test_invalid_yaml_creates_failed_trace(self, test_trace_dir, project_root):
        """잘못된 YAML 실행 시 FAILED trace 생성"""
        from nexous.core import Runner
        
        # 잘못된 YAML 생성
        invalid_yaml = test_trace_dir / "invalid.yaml"
        invalid_yaml.write_text("project_id: test\n# agents 없음")
        
        runner = Runner(
            trace_dir=str(test_trace_dir),
            preset_dir=str(project_root / "nexous" / "presets"),
            use_llm=False,
        )
        
        with pytest.raises(Exception):
            runner.run(str(invalid_yaml), run_id="invalid_yaml_test")
        
        # Trace 확인
        trace_path = test_trace_dir / "test" / "invalid_yaml_test" / "trace.json"
        if trace_path.exists():
            with open(trace_path) as f:
                trace_data = json.load(f)
            
            assert trace_data["status"] == "FAILED"
            assert len(trace_data.get("errors", [])) > 0
    
    def test_missing_preset_creates_failed_trace(self, test_trace_dir, project_root, tmp_path):
        """존재하지 않는 preset 사용 시 FAILED trace 생성"""
        from nexous.core import Runner
        
        # 잘못된 preset 참조하는 YAML
        bad_preset_yaml = tmp_path / "bad_preset.yaml"
        bad_preset_yaml.write_text("""
project_id: bad_preset_test
agents:
  - id: agent1
    preset: nonexistent_preset
    purpose: 테스트
""")
        
        runner = Runner(
            trace_dir=str(test_trace_dir),
            preset_dir=str(project_root / "nexous" / "presets"),
            use_llm=False,
        )
        
        with pytest.raises(Exception):
            runner.run(str(bad_preset_yaml), run_id="bad_preset_test")
        
        # Trace 확인
        trace_path = test_trace_dir / "bad_preset_test" / "bad_preset_test" / "trace.json"
        if trace_path.exists():
            with open(trace_path) as f:
                trace_data = json.load(f)
            
            assert trace_data["status"] == "FAILED"
    
    def test_error_contains_required_fields(self, test_trace_dir):
        """에러 기록에 필수 필드 포함 검증"""
        from nexous.core import TraceWriter
        
        trace = TraceWriter(base_dir=str(test_trace_dir))
        trace.start_run("error_fields_test", "error_test", "sequential")
        trace.start_agent("agent1", "tester", "테스트")
        
        # 에러 기록
        trace.log_error(
            agent_id="agent1",
            step_id="agent1.execute",
            error_type="TEST_ERROR",
            message="테스트 에러 메시지",
            recoverable=False,
        )
        
        trace.end_agent("agent1", "FAILED")
        trace.end_run("FAILED")
        
        trace_path = test_trace_dir / "error_fields_test" / "error_test" / "trace.json"
        with open(trace_path) as f:
            trace_data = json.load(f)
        
        assert trace_data["status"] == "FAILED"
        assert len(trace_data["errors"]) > 0
        
        error = trace_data["errors"][0]
        assert "agent_id" in error
        assert "type" in error
        assert "message" in error
        assert error["agent_id"] == "agent1"
        assert error["type"] == "TEST_ERROR"
    
    def test_failed_agent_status(self, test_trace_dir):
        """Agent 실패 시 status 검증"""
        from nexous.core import TraceWriter
        
        trace = TraceWriter(base_dir=str(test_trace_dir))
        trace.start_run("agent_fail_test", "status_test", "sequential")
        trace.start_agent("agent1", "tester", "테스트")
        trace.log_step("agent1", "INPUT", "OK", payload={})
        trace.log_step("agent1", "LLM", "ERROR", payload={"error": "API Error"})
        trace.end_agent("agent1", "FAILED")
        trace.end_run("FAILED")
        
        trace_path = test_trace_dir / "agent_fail_test" / "status_test" / "trace.json"
        with open(trace_path) as f:
            trace_data = json.load(f)
        
        assert trace_data["status"] == "FAILED"
        assert trace_data["agents"][0]["status"] == "FAILED"
        
        # 실패한 LLM step 확인
        llm_steps = [s for s in trace_data["agents"][0]["steps"] if s["type"] == "LLM"]
        assert llm_steps[0]["status"] == "ERROR"
    
    def test_tool_failure_recorded(self, test_trace_dir):
        """Tool 실패가 trace에 기록되는지 검증"""
        from nexous.core import TraceWriter
        
        trace = TraceWriter(base_dir=str(test_trace_dir))
        trace.start_run("tool_fail_test", "tool_error", "sequential")
        trace.start_agent("agent1", "executor", "실행")
        trace.log_step("agent1", "INPUT", "OK", payload={})
        trace.log_step("agent1", "TOOL", "ERROR", 
                      payload={"tool_name": "python_exec", "error": "SyntaxError"},
                      metadata={"latency_ms": 10})
        trace.end_agent("agent1", "COMPLETED")
        trace.end_run("COMPLETED")
        
        trace_path = test_trace_dir / "tool_fail_test" / "tool_error" / "trace.json"
        with open(trace_path) as f:
            trace_data = json.load(f)
        
        # TOOL step 확인
        tool_steps = [s for s in trace_data["agents"][0]["steps"] if s["type"] == "TOOL"]
        assert len(tool_steps) == 1
        assert tool_steps[0]["status"] == "ERROR"
    
    def test_llm_error_creates_failed_trace(self, test_trace_dir):
        """LLM 오류 시 FAILED trace 생성"""
        from nexous.core import TraceWriter
        from nexous.llm import LLMClientError
        
        trace = TraceWriter(base_dir=str(test_trace_dir))
        trace.start_run("llm_error_test", "llm_fail", "sequential")
        trace.start_agent("agent1", "tester", "테스트")
        
        # LLM 에러 기록
        trace.log_step("agent1", "LLM", "ERROR",
                      payload={"error": "API_KEY_MISSING"},
                      metadata={"provider": "openai"})
        
        trace.log_error(
            agent_id="agent1",
            step_id="agent1.llm",
            error_type="LLM_ERROR",
            message="OPENAI_API_KEY not set",
            recoverable=False,
        )
        
        trace.end_agent("agent1", "FAILED")
        trace.end_run("FAILED")
        
        trace_path = test_trace_dir / "llm_error_test" / "llm_fail" / "trace.json"
        with open(trace_path) as f:
            trace_data = json.load(f)
        
        assert trace_data["status"] == "FAILED"
        assert len(trace_data["errors"]) > 0
        assert trace_data["errors"][0]["type"] == "LLM_ERROR"
