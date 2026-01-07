"""
NEXOUS Test - LLM 호출 Trace 검증

실제 OpenAI LLM 호출 및 trace 기록 검증
"""

import os
import json
import pytest
from pathlib import Path


# OpenAI 키 없으면 전체 스킵 + E2E 마커
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY", "").startswith("sk-"),
        reason="OPENAI_API_KEY not set"
    )
]


class TestLLMTrace:
    """LLM 호출 Trace 검증"""
    
    def test_llm_call_recorded_in_trace(self, test_trace_dir):
        """LLM 호출이 trace에 기록되는지 검증"""
        from nexous.core import TraceWriter, GenericAgent
        
        # Trace 시작
        trace = TraceWriter(base_dir=str(test_trace_dir))
        trace.start_run("llm_test", "llm_trace_test", "sequential")
        trace.start_agent("test_agent", "tester", "LLM 테스트")
        
        # Agent 생성 및 실행
        agent = GenericAgent(
            agent_id="test_agent",
            role="tester",
            purpose="간단한 인사말 생성",
            llm_config={"provider": "openai", "model": "gpt-4o"},
            tools=[],
            system_prompt="한 문장으로 답하세요.",
            trace_callback=trace.log_step,
        )
        
        result = agent.execute({"inputs": {"task": "안녕하세요라고 답하세요"}})
        
        trace.end_agent("test_agent", "COMPLETED")
        trace.end_run("COMPLETED")
        
        # Trace 검증
        trace_path = test_trace_dir / "llm_test" / "llm_trace_test" / "trace.json"
        assert trace_path.exists()
        
        with open(trace_path) as f:
            trace_data = json.load(f)
        
        assert trace_data["status"] == "COMPLETED"
        assert trace_data["summary"]["total_llm_calls"] >= 1
    
    def test_llm_trace_contains_provider_and_model(self, test_trace_dir):
        """LLM trace에 provider/model 정보 포함 검증"""
        from nexous.core import TraceWriter, GenericAgent
        
        trace = TraceWriter(base_dir=str(test_trace_dir))
        trace.start_run("llm_meta_test", "meta_test", "sequential")
        trace.start_agent("agent1", "tester", "메타 테스트")
        
        agent = GenericAgent(
            agent_id="agent1",
            role="tester",
            purpose="테스트",
            llm_config={"provider": "openai", "model": "gpt-4o"},
            tools=[],
            trace_callback=trace.log_step,
        )
        
        agent.execute({"inputs": {"task": "1+1=?"}})
        
        trace.end_agent("agent1", "COMPLETED")
        trace.end_run("COMPLETED")
        
        # Trace 검증
        trace_path = test_trace_dir / "llm_meta_test" / "meta_test" / "trace.json"
        with open(trace_path) as f:
            trace_data = json.load(f)
        
        # LLM step 찾기
        llm_steps = []
        for agent in trace_data["agents"]:
            for step in agent["steps"]:
                if step["type"] == "LLM":
                    llm_steps.append(step)
        
        assert len(llm_steps) >= 1
        
        llm_step = llm_steps[0]
        assert llm_step["provider"] == "openai"
        assert llm_step["model"] == "gpt-4o"
    
    def test_llm_trace_contains_tokens(self, test_trace_dir):
        """LLM trace에 토큰 사용량 포함 검증"""
        from nexous.core import TraceWriter, GenericAgent
        
        trace = TraceWriter(base_dir=str(test_trace_dir))
        trace.start_run("token_test", "token_trace", "sequential")
        trace.start_agent("agent1", "tester", "토큰 테스트")
        
        agent = GenericAgent(
            agent_id="agent1",
            role="tester",
            purpose="토큰 테스트",
            llm_config={"provider": "openai", "model": "gpt-4o"},
            tools=[],
            trace_callback=trace.log_step,
        )
        
        agent.execute({"inputs": {"task": "Hello"}})
        
        trace.end_agent("agent1", "COMPLETED")
        trace.end_run("COMPLETED")
        
        # Trace 검증
        trace_path = test_trace_dir / "token_test" / "token_trace" / "trace.json"
        with open(trace_path) as f:
            trace_data = json.load(f)
        
        # 토큰 정보 확인
        assert trace_data["summary"]["total_tokens"] > 0
        
        # LLM step의 토큰 정보
        for agent in trace_data["agents"]:
            for step in agent["steps"]:
                if step["type"] == "LLM":
                    assert "tokens" in step
                    assert step["tokens"]["input"] > 0
                    assert step["tokens"]["output"] > 0
    
    def test_llm_trace_contains_latency(self, test_trace_dir):
        """LLM trace에 latency 포함 검증"""
        from nexous.core import TraceWriter, GenericAgent
        
        trace = TraceWriter(base_dir=str(test_trace_dir))
        trace.start_run("latency_test", "latency_trace", "sequential")
        trace.start_agent("agent1", "tester", "지연 테스트")
        
        agent = GenericAgent(
            agent_id="agent1",
            role="tester",
            purpose="지연 테스트",
            llm_config={"provider": "openai", "model": "gpt-4o"},
            tools=[],
            trace_callback=trace.log_step,
        )
        
        agent.execute({"inputs": {"task": "Hi"}})
        
        trace.end_agent("agent1", "COMPLETED")
        trace.end_run("COMPLETED")
        
        # Trace 검증
        trace_path = test_trace_dir / "latency_test" / "latency_trace" / "trace.json"
        with open(trace_path) as f:
            trace_data = json.load(f)
        
        # LLM step의 latency 정보
        for agent in trace_data["agents"]:
            for step in agent["steps"]:
                if step["type"] == "LLM":
                    assert "latency_ms" in step
                    assert step["latency_ms"] > 0
