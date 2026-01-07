"""
NEXOUS Test - Trace Schema 검증

trace.json이 trace_schema.json을 만족하는지 검증
"""

import os
import json
import pytest
from pathlib import Path

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


# Trace Schema 정의
TRACE_SCHEMA = {
    "type": "object",
    "required": ["run_id", "project_id", "status", "agents", "summary"],
    "properties": {
        "run_id": {"type": "string"},
        "project_id": {"type": "string"},
        "status": {
            "type": "string",
            "enum": ["RUNNING", "COMPLETED", "FAILED"]
        },
        "started_at": {"type": "string"},
        "ended_at": {"type": "string"},
        "duration_ms": {"type": "integer"},
        "execution_mode": {"type": "string"},
        "agents": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["agent_id", "status", "steps"],
                "properties": {
                    "agent_id": {"type": "string"},
                    "preset": {"type": "string"},
                    "purpose": {"type": "string"},
                    "status": {"type": "string"},
                    "steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["step_id", "type", "status"],
                            "properties": {
                                "step_id": {"type": "string"},
                                "type": {
                                    "type": "string",
                                    "enum": ["INPUT", "LLM", "TOOL", "OUTPUT"]
                                },
                                "status": {
                                    "type": "string",
                                    "enum": ["OK", "ERROR"]
                                }
                            }
                        }
                    }
                }
            }
        },
        "summary": {
            "type": "object",
            "required": ["total_agents", "total_llm_calls", "total_tool_calls", "total_tokens"],
            "properties": {
                "total_agents": {"type": "integer"},
                "completed_agents": {"type": "integer"},
                "failed_agents": {"type": "integer"},
                "total_llm_calls": {"type": "integer"},
                "total_tool_calls": {"type": "integer"},
                "total_tokens": {"type": "integer"}
            }
        },
        "errors": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["agent_id", "type", "message"],
                "properties": {
                    "agent_id": {"type": "string"},
                    "step_id": {"type": "string"},
                    "type": {"type": "string"},
                    "message": {"type": "string"}
                }
            }
        }
    }
}


class TestTraceSchema:
    """Trace Schema 검증"""
    
    def test_trace_has_required_fields(self, test_trace_dir):
        """trace.json에 필수 필드 존재 검증"""
        from nexous.core import TraceWriter
        
        trace = TraceWriter(base_dir=str(test_trace_dir))
        trace.start_run("schema_test", "required_fields", "sequential")
        trace.start_agent("agent1", "tester", "테스트")
        trace.log_step("agent1", "INPUT", "OK", payload={})
        trace.log_step("agent1", "OUTPUT", "OK", payload={})
        trace.end_agent("agent1", "COMPLETED")
        trace.end_run("COMPLETED")
        
        trace_path = test_trace_dir / "schema_test" / "required_fields" / "trace.json"
        with open(trace_path) as f:
            trace_data = json.load(f)
        
        # 필수 필드 확인
        assert "run_id" in trace_data
        assert "project_id" in trace_data
        assert "status" in trace_data
        assert "agents" in trace_data
        assert "summary" in trace_data
    
    def test_trace_status_enum(self, test_trace_dir):
        """trace status가 유효한 값인지 검증"""
        from nexous.core import TraceWriter
        
        trace = TraceWriter(base_dir=str(test_trace_dir))
        trace.start_run("status_test", "enum_test", "sequential")
        trace.end_run("COMPLETED")
        
        trace_path = test_trace_dir / "status_test" / "enum_test" / "trace.json"
        with open(trace_path) as f:
            trace_data = json.load(f)
        
        assert trace_data["status"] in ["RUNNING", "COMPLETED", "FAILED"]
    
    def test_trace_agent_structure(self, test_trace_dir):
        """agent 구조 검증"""
        from nexous.core import TraceWriter
        
        trace = TraceWriter(base_dir=str(test_trace_dir))
        trace.start_run("agent_test", "structure_test", "sequential")
        trace.start_agent("test_agent", "executor", "실행")
        trace.log_step("test_agent", "INPUT", "OK", payload={"context": []})
        trace.log_step("test_agent", "OUTPUT", "OK", payload={"output_keys": []})
        trace.end_agent("test_agent", "COMPLETED")
        trace.end_run("COMPLETED")
        
        trace_path = test_trace_dir / "agent_test" / "structure_test" / "trace.json"
        with open(trace_path) as f:
            trace_data = json.load(f)
        
        assert len(trace_data["agents"]) == 1
        agent = trace_data["agents"][0]
        
        assert "agent_id" in agent
        assert "status" in agent
        assert "steps" in agent
        assert agent["agent_id"] == "test_agent"
    
    def test_trace_step_types(self, test_trace_dir):
        """step type이 유효한 값인지 검증"""
        from nexous.core import TraceWriter
        
        trace = TraceWriter(base_dir=str(test_trace_dir))
        trace.start_run("step_test", "type_test", "sequential")
        trace.start_agent("agent1", "tester", "테스트")
        trace.log_step("agent1", "INPUT", "OK", payload={})
        trace.log_step("agent1", "LLM", "OK", payload={}, metadata={"provider": "openai"})
        trace.log_step("agent1", "TOOL", "OK", payload={"tool_name": "python_exec"})
        trace.log_step("agent1", "OUTPUT", "OK", payload={})
        trace.end_agent("agent1", "COMPLETED")
        trace.end_run("COMPLETED")
        
        trace_path = test_trace_dir / "step_test" / "type_test" / "trace.json"
        with open(trace_path) as f:
            trace_data = json.load(f)
        
        valid_types = {"INPUT", "LLM", "TOOL", "OUTPUT"}
        for agent in trace_data["agents"]:
            for step in agent["steps"]:
                assert step["type"] in valid_types
    
    def test_trace_summary_structure(self, test_trace_dir):
        """summary 구조 검증"""
        from nexous.core import TraceWriter
        
        trace = TraceWriter(base_dir=str(test_trace_dir))
        trace.start_run("summary_test", "struct_test", "sequential")
        trace.start_agent("agent1", "tester", "테스트")
        trace.end_agent("agent1", "COMPLETED")
        trace.end_run("COMPLETED")
        
        trace_path = test_trace_dir / "summary_test" / "struct_test" / "trace.json"
        with open(trace_path) as f:
            trace_data = json.load(f)
        
        summary = trace_data["summary"]
        
        assert "total_agents" in summary
        assert "total_llm_calls" in summary
        assert "total_tool_calls" in summary
        assert "total_tokens" in summary
        
        assert isinstance(summary["total_agents"], int)
        assert isinstance(summary["total_llm_calls"], int)
        assert isinstance(summary["total_tool_calls"], int)
        assert isinstance(summary["total_tokens"], int)
    
    @pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
    def test_trace_validates_against_schema(self, test_trace_dir):
        """trace.json이 전체 스키마를 만족하는지 검증"""
        from nexous.core import TraceWriter
        
        trace = TraceWriter(base_dir=str(test_trace_dir))
        trace.start_run("full_schema_test", "validation_test", "sequential")
        trace.start_agent("agent1", "executor", "실행")
        trace.log_step("agent1", "INPUT", "OK", payload={"context": []})
        trace.log_step("agent1", "LLM", "OK", 
                      payload={"input_summary": "test"},
                      metadata={"provider": "openai", "model": "gpt-4o", "tokens_input": 10, "tokens_output": 20})
        trace.log_step("agent1", "TOOL", "OK",
                      payload={"tool_name": "python_exec"},
                      metadata={"latency_ms": 100})
        trace.log_step("agent1", "OUTPUT", "OK", payload={"output_keys": ["result"]})
        trace.end_agent("agent1", "COMPLETED")
        trace.end_run("COMPLETED")
        
        trace_path = test_trace_dir / "full_schema_test" / "validation_test" / "trace.json"
        with open(trace_path) as f:
            trace_data = json.load(f)
        
        # JSON Schema 검증
        jsonschema.validate(instance=trace_data, schema=TRACE_SCHEMA)
