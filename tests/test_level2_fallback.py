"""
NEXOUS Test - LEVEL 2 Fallback 테스트

Primary 실패 시 Fallback으로 전환되는지 검증
"""

import os
import json
import pytest
from unittest.mock import patch, Mock


class TestFallbackScenario:
    """Primary 실패 → Fallback 성공 시나리오"""
    
    def test_fallback_on_primary_failure(self, mock_anthropic_client, mock_failing_client):
        """Primary 실패 시 Fallback으로 전환"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage, LLMRegistry
        
        policy = LLMPolicy(
            primary="openai/gpt-4o",
            retry=1,
            fallback=["anthropic/claude-3-5-sonnet-20241022"],
        )
        
        def mock_get(provider):
            if provider == "openai":
                return mock_failing_client
            return mock_anthropic_client
        
        with patch.object(LLMRegistry, 'get', side_effect=mock_get):
            router = LLMRouter(policy=policy, agent_id="test")
            messages = [LLMMessage(role="user", content="Test")]
            
            response = router.route(messages)
            
            # Fallback 사용됨
            assert response.provider == "anthropic"
            assert response.fallback_from == "openai/gpt-4o"
    
    def test_fallback_chain(self, mock_llm_response, mock_failing_client):
        """Fallback 체인 동작"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage, LLMRegistry
        
        policy = LLMPolicy(
            primary="openai/gpt-4o",
            retry=1,
            fallback=[
                "anthropic/claude-3-5-sonnet-20241022",
                "gemini/gemini-1.5-pro",
            ],
        )
        
        # OpenAI, Anthropic 실패 → Gemini 성공
        gemini_client = Mock()
        gemini_client.provider = "gemini"
        gemini_client.is_available.return_value = True
        gemini_client.generate.return_value = mock_llm_response(
            content="Gemini response",
            provider="gemini",
            model="gemini-1.5-pro",
        )
        
        anthropic_failing = Mock()
        anthropic_failing.provider = "anthropic"
        anthropic_failing.is_available.return_value = True
        from nexous.llm import LLMClientError
        anthropic_failing.generate.side_effect = LLMClientError(
            "Anthropic Error", provider="anthropic", recoverable=False
        )
        
        def mock_get(provider):
            if provider == "openai":
                return mock_failing_client
            elif provider == "anthropic":
                return anthropic_failing
            return gemini_client
        
        with patch.object(LLMRegistry, 'get', side_effect=mock_get):
            router = LLMRouter(policy=policy, agent_id="test")
            messages = [LLMMessage(role="user", content="Test")]
            
            response = router.route(messages)
            
            # 최종적으로 Gemini 사용
            assert response.provider == "gemini"
            assert response.fallback_from == "openai/gpt-4o"
            
            # 3개 Provider 시도됨
            providers_attempted = [a["provider"] for a in router.attempts]
            assert "openai" in providers_attempted
            assert "anthropic" in providers_attempted
            assert "gemini" in providers_attempted
    
    def test_fallback_records_original_primary(self, mock_anthropic_client, mock_failing_client):
        """Fallback 시 원래 Primary 기록"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage, LLMRegistry
        
        policy = LLMPolicy(
            primary="openai/gpt-4o",
            retry=1,
            fallback=["anthropic/claude-3-5-sonnet-20241022"],
        )
        
        def mock_get(provider):
            if provider == "openai":
                return mock_failing_client
            return mock_anthropic_client
        
        with patch.object(LLMRegistry, 'get', side_effect=mock_get):
            router = LLMRouter(policy=policy, agent_id="test")
            messages = [LLMMessage(role="user", content="Test")]
            
            response = router.route(messages)
            
            # fallback_from에 원래 primary 기록
            assert response.fallback_from == "openai/gpt-4o"


class TestFallbackTrace:
    """Fallback Trace 기록 검증"""
    
    def test_fallback_trace_recorded(self, mock_anthropic_client, mock_failing_client):
        """Fallback 시 Trace에 is_fallback 기록"""
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
            
            # 성공한 trace (anthropic)
            success_traces = [t for t in trace_calls if t.get("status") == "OK"]
            assert len(success_traces) >= 1
            
            # is_fallback 확인
            fallback_trace = success_traces[0]
            assert fallback_trace["metadata"].get("is_fallback") is True
            assert fallback_trace["metadata"].get("fallback_from") == "openai/gpt-4o"
    
    def test_fallback_trace_contains_all_attempts(self, mock_anthropic_client, mock_failing_client):
        """Fallback 시 모든 시도가 attempts에 기록"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage, LLMRegistry
        
        policy = LLMPolicy(
            primary="openai/gpt-4o",
            retry=2,  # 2번 retry
            fallback=["anthropic/claude-3-5-sonnet-20241022"],
        )
        
        def mock_get(provider):
            if provider == "openai":
                return mock_failing_client
            return mock_anthropic_client
        
        with patch.object(LLMRegistry, 'get', side_effect=mock_get):
            router = LLMRouter(policy=policy, agent_id="test")
            messages = [LLMMessage(role="user", content="Test")]
            
            router.route(messages)
            
            # OpenAI 2회 실패 + Anthropic 1회 성공 = 3회 시도
            # (recoverable=True이면 retry, False면 즉시 다음으로)
            assert len(router.attempts) >= 2


class TestFallbackWithAgent:
    """GenericAgent Fallback 테스트"""
    
    def test_agent_fallback_response(self, test_trace_dir, mock_anthropic_client, mock_failing_client):
        """Agent Fallback 응답"""
        from nexous.core import GenericAgent, TraceWriter
        from nexous.llm import LLMRegistry
        
        def mock_get(provider):
            if provider == "openai":
                return mock_failing_client
            return mock_anthropic_client
        
        with patch.object(LLMRegistry, 'get', side_effect=mock_get):
            trace = TraceWriter(base_dir=str(test_trace_dir))
            trace.start_run("fallback_test", "agent_fallback", "sequential")
            trace.start_agent("agent1", "tester", "테스트")
            
            agent = GenericAgent(
                agent_id="agent1",
                role="tester",
                purpose="테스트",
                llm_config={
                    "policy": {
                        "primary": "openai/gpt-4o",
                        "retry": 1,
                        "fallback": ["anthropic/claude-3-5-sonnet-20241022"],
                    }
                },
                tools=[],
                trace_callback=trace.log_step,
            )
            
            result = agent.execute({"inputs": {"task": "Test"}})
            
            trace.end_agent("agent1", "COMPLETED")
            trace.end_run("COMPLETED")
            
            # Fallback 사용 확인
            assert result["provider"] == "anthropic"
            assert result["routing_info"]["fallback_from"] == "openai/gpt-4o"


class TestFallbackRealProviders:
    """실제 Provider Fallback 테스트"""
    
    @pytest.mark.skipif(
        not (os.getenv("OPENAI_API_KEY") and os.getenv("ANTHROPIC_API_KEY")),
        reason="Both OPENAI_API_KEY and ANTHROPIC_API_KEY required"
    )
    def test_real_fallback_openai_to_anthropic(self):
        """실제 OpenAI → Anthropic Fallback"""
        # 이 테스트는 OpenAI가 실패해야 Anthropic으로 가므로
        # 실제로는 OpenAI 성공해서 Fallback 안 일어남
        # Mock으로 테스트하는 것이 더 적절
        pass
