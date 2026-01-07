"""
NEXOUS Test - LEVEL 2 전체 실패 검증

모든 LLM Provider 실패 시 trace.status=FAILED 검증
"""

import os
import json
import pytest
from unittest.mock import patch, Mock


class TestAllProvidersFailed:
    """모든 Provider 실패 시나리오"""
    
    def test_all_providers_failed_raises_error(self, mock_failing_client):
        """모든 Provider 실패 시 에러 발생"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage, LLMRegistry, LLMAllProvidersFailedError
        
        policy = LLMPolicy(
            primary="openai/gpt-4o",
            retry=1,
            fallback=["anthropic/claude-3-5-sonnet-20241022"],
        )
        
        with patch.object(LLMRegistry, 'get', return_value=mock_failing_client):
            router = LLMRouter(policy=policy, agent_id="test")
            messages = [LLMMessage(role="user", content="Test")]
            
            with pytest.raises(LLMAllProvidersFailedError) as exc_info:
                router.route(messages)
            
            # 에러에 attempts 포함
            assert len(exc_info.value.attempts) >= 2
    
    def test_all_failed_error_contains_attempts(self, mock_failing_client):
        """LLMAllProvidersFailedError에 시도 정보 포함"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage, LLMRegistry, LLMAllProvidersFailedError
        
        policy = LLMPolicy(
            primary="openai/gpt-4o",
            retry=2,
            fallback=["anthropic/claude-3-5-sonnet-20241022", "gemini/gemini-1.5-pro"],
        )
        
        with patch.object(LLMRegistry, 'get', return_value=mock_failing_client):
            router = LLMRouter(policy=policy, agent_id="test")
            messages = [LLMMessage(role="user", content="Test")]
            
            with pytest.raises(LLMAllProvidersFailedError) as exc_info:
                router.route(messages)
            
            # 모든 시도 기록
            attempts = exc_info.value.attempts
            providers_attempted = set(a["provider"] for a in attempts)
            
            # 3개 Provider 모두 시도됨
            assert "openai" in providers_attempted or "mock" in providers_attempted
    
    def test_all_failed_trace_recorded(self, mock_failing_client):
        """전체 실패 시 ERROR trace 기록"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage, LLMRegistry, LLMAllProvidersFailedError
        
        policy = LLMPolicy(
            primary="openai/gpt-4o",
            retry=1,
            fallback=[],
        )
        
        trace_calls = []
        def mock_trace(**kwargs):
            trace_calls.append(kwargs)
        
        with patch.object(LLMRegistry, 'get', return_value=mock_failing_client):
            router = LLMRouter(
                policy=policy,
                trace_callback=mock_trace,
                agent_id="test_agent",
            )
            messages = [LLMMessage(role="user", content="Test")]
            
            with pytest.raises(LLMAllProvidersFailedError):
                router.route(messages)
            
            # ERROR trace 기록됨
            error_traces = [t for t in trace_calls if t.get("status") == "ERROR"]
            assert len(error_traces) >= 1
            
            error_trace = error_traces[0]
            assert error_trace["step_type"] == "LLM"
            assert "All LLM providers failed" in error_trace["payload"].get("error", "")


class TestFailedTraceStatus:
    """실패 시 Trace Status"""
    
    def test_agent_failure_trace_status(self, test_trace_dir, mock_failing_client):
        """Agent 실패 시 trace status=FAILED"""
        from nexous.core import GenericAgent, TraceWriter
        from nexous.llm import LLMRegistry, LLMAllProvidersFailedError
        
        with patch.object(LLMRegistry, 'get', return_value=mock_failing_client):
            trace = TraceWriter(base_dir=str(test_trace_dir))
            trace.start_run("fail_test", "status_failed", "sequential")
            trace.start_agent("agent1", "tester", "테스트")
            
            agent = GenericAgent(
                agent_id="agent1",
                role="tester",
                purpose="테스트",
                llm_config={"policy": {"primary": "openai/gpt-4o", "retry": 1, "fallback": []}},
                tools=[],
                trace_callback=trace.log_step,
            )
            
            try:
                agent.execute({"inputs": {"task": "Test"}})
                trace.end_agent("agent1", "COMPLETED")
                trace.end_run("COMPLETED")
            except LLMAllProvidersFailedError:
                trace.log_error(
                    agent_id="agent1",
                    step_id="agent1.llm",
                    error_type="LLM_ALL_FAILED",
                    message="All LLM providers failed",
                    recoverable=False,
                )
                trace.end_agent("agent1", "FAILED")
                trace.end_run("FAILED")
            
            # Trace 검증
            trace_path = test_trace_dir / "fail_test" / "status_failed" / "trace.json"
            with open(trace_path) as f:
                trace_data = json.load(f)
            
            assert trace_data["status"] == "FAILED"
            assert len(trace_data["errors"]) >= 1
    
    def test_failed_trace_contains_error_info(self, test_trace_dir, mock_failing_client):
        """실패 trace에 에러 정보 포함"""
        from nexous.core import GenericAgent, TraceWriter
        from nexous.llm import LLMRegistry, LLMAllProvidersFailedError
        
        with patch.object(LLMRegistry, 'get', return_value=mock_failing_client):
            trace = TraceWriter(base_dir=str(test_trace_dir))
            trace.start_run("error_info_test", "error_detail", "sequential")
            trace.start_agent("agent1", "tester", "테스트")
            
            agent = GenericAgent(
                agent_id="agent1",
                role="tester",
                purpose="테스트",
                llm_config={"policy": {"primary": "openai/gpt-4o", "retry": 1, "fallback": []}},
                tools=[],
                trace_callback=trace.log_step,
            )
            
            try:
                agent.execute({"inputs": {"task": "Test"}})
            except LLMAllProvidersFailedError as e:
                trace.log_error(
                    agent_id="agent1",
                    step_id="agent1.llm",
                    error_type="LLM_ALL_FAILED",
                    message=str(e),
                    recoverable=False,
                )
                trace.end_agent("agent1", "FAILED")
                trace.end_run("FAILED")
            
            trace_path = test_trace_dir / "error_info_test" / "error_detail" / "trace.json"
            with open(trace_path) as f:
                trace_data = json.load(f)
            
            # 에러 정보
            error = trace_data["errors"][0]
            assert "agent_id" in error
            assert "type" in error
            assert "message" in error


class TestFailedSummary:
    """실패 시 Summary"""
    
    def test_failed_summary_counts(self, test_trace_dir, mock_failing_client):
        """실패 시 summary에 failed_agents 카운트"""
        from nexous.core import GenericAgent, TraceWriter
        from nexous.llm import LLMRegistry, LLMAllProvidersFailedError
        
        with patch.object(LLMRegistry, 'get', return_value=mock_failing_client):
            trace = TraceWriter(base_dir=str(test_trace_dir))
            trace.start_run("summary_fail", "fail_count", "sequential")
            trace.start_agent("agent1", "tester", "테스트")
            
            agent = GenericAgent(
                agent_id="agent1",
                role="tester",
                purpose="테스트",
                llm_config={"policy": {"primary": "openai/gpt-4o", "retry": 1, "fallback": []}},
                tools=[],
                trace_callback=trace.log_step,
            )
            
            try:
                agent.execute({"inputs": {"task": "Test"}})
                trace.end_agent("agent1", "COMPLETED")
            except LLMAllProvidersFailedError:
                trace.end_agent("agent1", "FAILED")
            
            trace.end_run("FAILED")
            
            trace_path = test_trace_dir / "summary_fail" / "fail_count" / "trace.json"
            with open(trace_path) as f:
                trace_data = json.load(f)
            
            # Summary
            summary = trace_data["summary"]
            assert summary["failed_agents"] >= 1


class TestPartialFailure:
    """부분 실패 (일부 Agent 성공)"""
    
    def test_partial_failure_trace(self, test_trace_dir, mock_openai_client, mock_failing_client):
        """일부 Agent만 실패"""
        from nexous.core import GenericAgent, TraceWriter
        from nexous.llm import LLMRegistry, LLMAllProvidersFailedError
        
        call_count = [0]
        
        def mock_get(provider):
            call_count[0] += 1
            if call_count[0] <= 1:  # 첫 번째 Agent는 성공
                return mock_openai_client
            return mock_failing_client  # 두 번째 Agent는 실패
        
        with patch.object(LLMRegistry, 'get', side_effect=mock_get):
            trace = TraceWriter(base_dir=str(test_trace_dir))
            trace.start_run("partial_fail", "partial_trace", "sequential")
            
            # Agent 1: 성공
            trace.start_agent("agent1", "planner", "계획")
            agent1 = GenericAgent(
                agent_id="agent1",
                role="planner",
                purpose="계획",
                llm_config={"policy": {"primary": "openai/gpt-4o", "retry": 1, "fallback": []}},
                tools=[],
                trace_callback=trace.log_step,
            )
            try:
                agent1.execute({"inputs": {"task": "Plan"}})
                trace.end_agent("agent1", "COMPLETED")
            except:
                trace.end_agent("agent1", "FAILED")
            
            # Agent 2: 실패
            trace.start_agent("agent2", "executor", "실행")
            agent2 = GenericAgent(
                agent_id="agent2",
                role="executor",
                purpose="실행",
                llm_config={"policy": {"primary": "openai/gpt-4o", "retry": 1, "fallback": []}},
                tools=[],
                trace_callback=trace.log_step,
            )
            try:
                agent2.execute({"inputs": {"task": "Execute"}})
                trace.end_agent("agent2", "COMPLETED")
            except:
                trace.end_agent("agent2", "FAILED")
            
            trace.end_run("FAILED")  # 하나라도 실패하면 FAILED
            
            trace_path = test_trace_dir / "partial_fail" / "partial_trace" / "trace.json"
            with open(trace_path) as f:
                trace_data = json.load(f)
            
            # 부분 실패
            summary = trace_data["summary"]
            assert summary["completed_agents"] >= 1 or summary["failed_agents"] >= 1
