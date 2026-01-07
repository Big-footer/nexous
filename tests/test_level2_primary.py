"""
NEXOUS Test - LEVEL 2 Primary LLM 성공 테스트

Primary LLM이 정상 작동하는 경우 검증
"""

import os
import json
import pytest
from unittest.mock import patch, Mock


class TestPrimaryLLMSuccess:
    """Primary LLM 성공 시나리오"""
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY", "").startswith("sk-"),
        reason="OPENAI_API_KEY not set"
    )
    def test_primary_openai_success(self):
        """OpenAI Primary 성공"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage
        
        policy = LLMPolicy(
            primary="openai/gpt-4o",
            retry=1,
            fallback=[],
        )
        
        router = LLMRouter(policy=policy, agent_id="test")
        messages = [LLMMessage(role="user", content="Say 'hello'")]
        
        response = router.route(messages)
        
        assert response.provider == "openai"
        assert response.model == "gpt-4o"
        assert response.attempt == 1
        assert response.fallback_from is None
        assert response.tokens_total > 0
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY", "").startswith("sk-"),
        reason="OPENAI_API_KEY not set"
    )
    def test_primary_success_no_fallback_used(self):
        """Primary 성공 시 Fallback 미사용"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage
        
        policy = LLMPolicy(
            primary="openai/gpt-4o",
            retry=1,
            fallback=["anthropic/claude-3-5-sonnet-20241022"],
        )
        
        router = LLMRouter(policy=policy, agent_id="test")
        messages = [LLMMessage(role="user", content="Hi")]
        
        response = router.route(messages)
        
        # Primary만 사용됨
        assert response.provider == "openai"
        assert response.fallback_from is None
        
        # attempts에 openai만 있어야 함
        providers_attempted = [a["provider"] for a in router.attempts]
        assert "openai" in providers_attempted
        assert "anthropic" not in providers_attempted
    
    def test_primary_success_mock(self, mock_openai_client, mock_llm_response):
        """Primary 성공 (Mock)"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage, LLMRegistry
        
        policy = LLMPolicy(
            primary="openai/gpt-4o",
            retry=1,
            fallback=[],
        )
        
        with patch.object(LLMRegistry, 'get', return_value=mock_openai_client):
            router = LLMRouter(policy=policy, agent_id="test")
            messages = [LLMMessage(role="user", content="Test")]
            
            response = router.route(messages)
            
            assert response.provider == "openai"
            assert mock_openai_client.generate.called
            assert len(router.attempts) == 1
            assert router.attempts[0]["success"] is True
    
    def test_primary_response_contains_required_fields(self, mock_openai_client):
        """응답에 필수 필드 포함 확인"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage, LLMRegistry
        
        policy = LLMPolicy(primary="openai/gpt-4o", retry=1)
        
        with patch.object(LLMRegistry, 'get', return_value=mock_openai_client):
            router = LLMRouter(policy=policy, agent_id="test")
            messages = [LLMMessage(role="user", content="Test")]
            
            response = router.route(messages)
            
            # 필수 필드
            assert hasattr(response, 'content')
            assert hasattr(response, 'provider')
            assert hasattr(response, 'model')
            assert hasattr(response, 'tokens_input')
            assert hasattr(response, 'tokens_output')
            assert hasattr(response, 'latency_ms')
            assert hasattr(response, 'attempt')
            assert hasattr(response, 'fallback_from')


class TestPrimaryLLMWithTrace:
    """Primary LLM + Trace 기록"""
    
    def test_primary_success_trace_recorded(self, mock_openai_client):
        """Primary 성공 시 Trace 기록"""
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
            
            # Trace 기록됨
            assert len(trace_calls) >= 1
            
            llm_trace = trace_calls[0]
            assert llm_trace["agent_id"] == "test_agent"
            assert llm_trace["step_type"] == "LLM"
            assert llm_trace["status"] == "OK"
            assert "provider" in llm_trace["metadata"]
            assert "model" in llm_trace["metadata"]
    
    def test_primary_trace_contains_tokens(self, mock_openai_client):
        """Trace에 토큰 정보 포함"""
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
            
            metadata = trace_calls[0]["metadata"]
            assert "tokens_input" in metadata
            assert "tokens_output" in metadata
            assert metadata["tokens_input"] > 0
            assert metadata["tokens_output"] > 0


class TestGenericAgentPrimary:
    """GenericAgent Primary 테스트"""
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY", "").startswith("sk-"),
        reason="OPENAI_API_KEY not set"
    )
    def test_agent_primary_success(self):
        """Agent가 Primary LLM 사용"""
        from nexous.core import GenericAgent
        
        agent = GenericAgent(
            agent_id="primary_agent",
            role="tester",
            purpose="테스트",
            llm_config={
                "policy": {
                    "primary": "openai/gpt-4o",
                    "retry": 1,
                    "fallback": [],
                }
            },
            tools=[],
        )
        
        result = agent.execute({"inputs": {"task": "Say hello"}})
        
        assert result["status"] == "success"
        assert result["provider"] == "openai"
        assert result["model"] == "gpt-4o"
        assert result["routing_info"]["fallback_from"] is None
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY", "").startswith("sk-"),
        reason="OPENAI_API_KEY not set"
    )
    def test_agent_primary_with_trace(self, test_trace_dir):
        """Agent Primary + Trace 기록"""
        from nexous.core import GenericAgent, TraceWriter
        
        trace = TraceWriter(base_dir=str(test_trace_dir))
        trace.start_run("primary_test", "agent_trace", "sequential")
        trace.start_agent("agent1", "tester", "테스트")
        
        agent = GenericAgent(
            agent_id="agent1",
            role="tester",
            purpose="테스트",
            llm_config={
                "policy": {"primary": "openai/gpt-4o", "retry": 1}
            },
            tools=[],
            trace_callback=trace.log_step,
        )
        
        agent.execute({"inputs": {"task": "Hi"}})
        
        trace.end_agent("agent1", "COMPLETED")
        trace.end_run("COMPLETED")
        
        # Trace 검증
        trace_path = test_trace_dir / "primary_test" / "agent_trace" / "trace.json"
        with open(trace_path) as f:
            trace_data = json.load(f)
        
        assert trace_data["status"] == "COMPLETED"
        assert trace_data["summary"]["total_llm_calls"] >= 1
        
        # LLM step 확인
        llm_steps = []
        for agent_data in trace_data["agents"]:
            for step in agent_data["steps"]:
                if step["type"] == "LLM":
                    llm_steps.append(step)
        
        assert len(llm_steps) >= 1
        assert llm_steps[0]["provider"] == "openai"
