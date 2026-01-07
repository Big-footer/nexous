"""
NEXOUS Test - LEVEL 2 Trace 기록 검증

모든 LLM step이 Trace에 기록되는지 검증
"""

import os
import json
import pytest
from unittest.mock import patch, Mock


class TestLLMStepTrace:
    """LLM Step Trace 기록"""
    
    def test_llm_step_recorded(self, mock_openai_client):
        """LLM step이 Trace에 기록"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage, LLMRegistry
        
        policy = LLMPolicy(primary="openai/gpt-4o", retry=1)
        
        trace_calls = []
        def mock_trace(**kwargs):
            trace_calls.append(kwargs)
        
        with patch.object(LLMRegistry, 'get', return_value=mock_openai_client):
            router = LLMRouter(
                policy=policy,
                trace_callback=mock_trace,
                agent_id="test_agent",
            )
            messages = [LLMMessage(role="user", content="Test")]
            
            router.route(messages)
            
            # LLM step 기록됨
            llm_traces = [t for t in trace_calls if t.get("step_type") == "LLM"]
            assert len(llm_traces) >= 1
    
    def test_llm_step_contains_required_fields(self, mock_openai_client):
        """LLM step에 필수 필드 포함"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage, LLMRegistry
        
        policy = LLMPolicy(primary="openai/gpt-4o", retry=1)
        
        trace_calls = []
        def mock_trace(**kwargs):
            trace_calls.append(kwargs)
        
        with patch.object(LLMRegistry, 'get', return_value=mock_openai_client):
            router = LLMRouter(
                policy=policy,
                trace_callback=mock_trace,
                agent_id="test_agent",
            )
            messages = [LLMMessage(role="user", content="Test")]
            
            router.route(messages)
            
            llm_trace = trace_calls[0]
            
            # 필수 필드
            assert "agent_id" in llm_trace
            assert "step_type" in llm_trace
            assert "status" in llm_trace
            assert "payload" in llm_trace
            assert "metadata" in llm_trace
            
            # 메타데이터 필수 필드
            metadata = llm_trace["metadata"]
            assert "provider" in metadata
            assert "model" in metadata
            assert "tokens_input" in metadata
            assert "tokens_output" in metadata
            assert "latency_ms" in metadata
    
    def test_llm_step_status_ok_on_success(self, mock_openai_client):
        """성공 시 status=OK"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage, LLMRegistry
        
        policy = LLMPolicy(primary="openai/gpt-4o", retry=1)
        
        trace_calls = []
        def mock_trace(**kwargs):
            trace_calls.append(kwargs)
        
        with patch.object(LLMRegistry, 'get', return_value=mock_openai_client):
            router = LLMRouter(
                policy=policy,
                trace_callback=mock_trace,
                agent_id="test",
            )
            messages = [LLMMessage(role="user", content="Test")]
            
            router.route(messages)
            
            llm_trace = trace_calls[0]
            assert llm_trace["status"] == "OK"
    
    def test_llm_step_status_error_on_all_failed(self, mock_failing_client):
        """전체 실패 시 status=ERROR"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage, LLMRegistry, LLMAllProvidersFailedError
        
        policy = LLMPolicy(primary="openai/gpt-4o", retry=1, fallback=[])
        
        trace_calls = []
        def mock_trace(**kwargs):
            trace_calls.append(kwargs)
        
        with patch.object(LLMRegistry, 'get', return_value=mock_failing_client):
            router = LLMRouter(
                policy=policy,
                trace_callback=mock_trace,
                agent_id="test",
            )
            messages = [LLMMessage(role="user", content="Test")]
            
            with pytest.raises(LLMAllProvidersFailedError):
                router.route(messages)
            
            # ERROR trace 기록됨
            error_traces = [t for t in trace_calls if t.get("status") == "ERROR"]
            assert len(error_traces) >= 1


class TestMultipleLLMSteps:
    """다중 LLM Step 기록"""
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY", "").startswith("sk-"),
        reason="OPENAI_API_KEY not set"
    )
    def test_multiple_agents_trace(self, test_trace_dir):
        """여러 Agent의 LLM step 기록"""
        from nexous.core import TraceWriter, GenericAgent
        
        trace = TraceWriter(base_dir=str(test_trace_dir))
        trace.start_run("multi_agent", "multi_trace", "sequential")
        
        # Agent 1
        trace.start_agent("agent1", "planner", "계획")
        agent1 = GenericAgent(
            agent_id="agent1",
            role="planner",
            purpose="계획 수립",
            llm_config={"policy": {"primary": "openai/gpt-4o", "retry": 1}},
            tools=[],
            trace_callback=trace.log_step,
        )
        agent1.execute({"inputs": {"task": "Plan"}})
        trace.end_agent("agent1", "COMPLETED")
        
        # Agent 2
        trace.start_agent("agent2", "executor", "실행")
        agent2 = GenericAgent(
            agent_id="agent2",
            role="executor",
            purpose="실행",
            llm_config={"policy": {"primary": "openai/gpt-4o", "retry": 1}},
            tools=[],
            trace_callback=trace.log_step,
        )
        agent2.execute({"inputs": {"task": "Execute"}})
        trace.end_agent("agent2", "COMPLETED")
        
        trace.end_run("COMPLETED")
        
        # Trace 검증
        trace_path = test_trace_dir / "multi_agent" / "multi_trace" / "trace.json"
        with open(trace_path) as f:
            trace_data = json.load(f)
        
        # 2개 Agent
        assert len(trace_data["agents"]) == 2
        
        # 각 Agent에 LLM step
        for agent_data in trace_data["agents"]:
            llm_steps = [s for s in agent_data["steps"] if s["type"] == "LLM"]
            assert len(llm_steps) >= 1


class TestTraceWithFallback:
    """Fallback Trace 기록"""
    
    def test_fallback_trace_contains_is_fallback(self, mock_anthropic_client, mock_failing_client):
        """Fallback trace에 is_fallback 포함"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage, LLMRegistry
        
        policy = LLMPolicy(
            primary="openai/gpt-4o",
            retry=1,
            fallback=["anthropic/claude-3-5-sonnet-20241022"],
        )
        
        trace_calls = []
        def mock_trace(**kwargs):
            trace_calls.append(kwargs)
        
        def mock_get(provider):
            if provider == "openai":
                return mock_failing_client
            return mock_anthropic_client
        
        with patch.object(LLMRegistry, 'get', side_effect=mock_get):
            router = LLMRouter(
                policy=policy,
                trace_callback=mock_trace,
                agent_id="test",
            )
            messages = [LLMMessage(role="user", content="Test")]
            
            router.route(messages)
            
            # 성공 trace (anthropic)
            success_traces = [t for t in trace_calls if t.get("status") == "OK"]
            assert len(success_traces) >= 1
            
            # is_fallback 확인
            metadata = success_traces[0]["metadata"]
            assert metadata.get("is_fallback") is True
            assert metadata.get("fallback_from") == "openai/gpt-4o"
    
    def test_fallback_trace_contains_provider_info(self, mock_anthropic_client, mock_failing_client):
        """Fallback trace에 실제 사용된 provider 정보"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage, LLMRegistry
        
        policy = LLMPolicy(
            primary="openai/gpt-4o",
            retry=1,
            fallback=["anthropic/claude-3-5-sonnet-20241022"],
        )
        
        trace_calls = []
        def mock_trace(**kwargs):
            trace_calls.append(kwargs)
        
        def mock_get(provider):
            if provider == "openai":
                return mock_failing_client
            return mock_anthropic_client
        
        with patch.object(LLMRegistry, 'get', side_effect=mock_get):
            router = LLMRouter(
                policy=policy,
                trace_callback=mock_trace,
                agent_id="test",
            )
            messages = [LLMMessage(role="user", content="Test")]
            
            router.route(messages)
            
            success_traces = [t for t in trace_calls if t.get("status") == "OK"]
            metadata = success_traces[0]["metadata"]
            
            # 실제 사용된 provider
            assert metadata["provider"] == "anthropic"
            assert metadata["model"] == "claude-3-5-sonnet-20241022"


class TestTraceSummary:
    """Trace Summary 검증"""
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY", "").startswith("sk-"),
        reason="OPENAI_API_KEY not set"
    )
    def test_trace_summary_llm_calls(self, test_trace_dir):
        """Summary에 total_llm_calls 포함"""
        from nexous.core import TraceWriter, GenericAgent
        
        trace = TraceWriter(base_dir=str(test_trace_dir))
        trace.start_run("summary_test", "llm_calls", "sequential")
        trace.start_agent("agent1", "tester", "테스트")
        
        agent = GenericAgent(
            agent_id="agent1",
            role="tester",
            purpose="테스트",
            llm_config={"policy": {"primary": "openai/gpt-4o", "retry": 1}},
            tools=[],
            trace_callback=trace.log_step,
        )
        
        agent.execute({"inputs": {"task": "Test"}})
        
        trace.end_agent("agent1", "COMPLETED")
        trace.end_run("COMPLETED")
        
        # Summary 확인
        trace_path = test_trace_dir / "summary_test" / "llm_calls" / "trace.json"
        with open(trace_path) as f:
            trace_data = json.load(f)
        
        assert trace_data["summary"]["total_llm_calls"] >= 1
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY", "").startswith("sk-"),
        reason="OPENAI_API_KEY not set"
    )
    def test_trace_summary_tokens(self, test_trace_dir):
        """Summary에 total_tokens 포함"""
        from nexous.core import TraceWriter, GenericAgent
        
        trace = TraceWriter(base_dir=str(test_trace_dir))
        trace.start_run("tokens_test", "token_trace", "sequential")
        trace.start_agent("agent1", "tester", "테스트")
        
        agent = GenericAgent(
            agent_id="agent1",
            role="tester",
            purpose="테스트",
            llm_config={"policy": {"primary": "openai/gpt-4o", "retry": 1}},
            tools=[],
            trace_callback=trace.log_step,
        )
        
        agent.execute({"inputs": {"task": "Hi"}})
        
        trace.end_agent("agent1", "COMPLETED")
        trace.end_run("COMPLETED")
        
        trace_path = test_trace_dir / "tokens_test" / "token_trace" / "trace.json"
        with open(trace_path) as f:
            trace_data = json.load(f)
        
        assert trace_data["summary"]["total_tokens"] > 0
