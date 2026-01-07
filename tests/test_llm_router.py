"""
NEXOUS Test - LLM Router 테스트

LEVEL 2:
- 성공 시나리오
- 폴백 시나리오
- 전체 실패 시나리오
"""

import os
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


class TestLLMPolicy:
    """LLMPolicy 테스트"""
    
    def test_policy_from_dict(self):
        """딕셔너리에서 Policy 생성"""
        from nexous.llm import LLMPolicy
        
        data = {
            "primary": "openai/gpt-4o",
            "retry": 3,
            "fallback": ["anthropic/claude-3-5-sonnet-20241022", "gemini/gemini-pro"],
            "timeout": 60,
        }
        
        policy = LLMPolicy.from_dict(data)
        
        assert policy.primary == "openai/gpt-4o"
        assert policy.retry == 3
        assert len(policy.fallback) == 2
    
    def test_policy_get_provider_model(self):
        """provider/model 파싱"""
        from nexous.llm import LLMPolicy
        
        policy = LLMPolicy(primary="openai/gpt-4o")
        
        provider, model = policy.get_provider_model("openai/gpt-4o")
        assert provider == "openai"
        assert model == "gpt-4o"
        
        provider, model = policy.get_provider_model("anthropic/claude-3-5-sonnet-20241022")
        assert provider == "anthropic"
        assert model == "claude-3-5-sonnet-20241022"


class TestLLMRegistry:
    """LLMRegistry 테스트"""
    
    def test_list_providers(self):
        """Provider 목록"""
        from nexous.llm import LLMRegistry
        
        providers = LLMRegistry.list_providers()
        
        assert "openai" in providers
        assert "anthropic" in providers
        assert "gemini" in providers
    
    def test_get_openai_client(self):
        """OpenAI Client 획득"""
        from nexous.llm import LLMRegistry
        
        client = LLMRegistry.get("openai")
        assert client.provider == "openai"
    
    def test_get_unknown_provider(self):
        """알 수 없는 Provider"""
        from nexous.llm import LLMRegistry, LLMClientError
        
        with pytest.raises(LLMClientError):
            LLMRegistry.get("unknown_provider")


class TestLLMRouterSuccess:
    """LLM Router 성공 시나리오"""
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY", "").startswith("sk-"),
        reason="OPENAI_API_KEY not set"
    )
    def test_router_primary_success(self):
        """Primary 성공"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage
        
        policy = LLMPolicy(
            primary="openai/gpt-4o",
            retry=1,
        )
        
        router = LLMRouter(policy=policy, agent_id="test")
        
        messages = [
            LLMMessage(role="user", content="Say 'Hello'")
        ]
        
        response = router.route(messages)
        
        assert response.provider == "openai"
        assert response.model == "gpt-4o"
        assert response.attempt == 1
        assert response.fallback_from is None
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY", "").startswith("sk-"),
        reason="OPENAI_API_KEY not set"
    )
    def test_router_trace_callback(self):
        """Trace callback 호출"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage
        
        policy = LLMPolicy(primary="openai/gpt-4o", retry=1)
        
        trace_calls = []
        def mock_trace(**kwargs):
            trace_calls.append(kwargs)
        
        router = LLMRouter(
            policy=policy,
            trace_callback=mock_trace,
            agent_id="test_agent",
        )
        
        messages = [LLMMessage(role="user", content="Hi")]
        router.route(messages)
        
        assert len(trace_calls) >= 1
        assert trace_calls[0]["agent_id"] == "test_agent"
        assert trace_calls[0]["step_type"] == "LLM"


class TestLLMRouterFallback:
    """LLM Router 폴백 시나리오"""
    
    def test_router_fallback_on_primary_failure(self):
        """Primary 실패 시 Fallback"""
        from nexous.llm import (
            LLMRouter, LLMPolicy, LLMMessage,
            LLMClientError, LLMRegistry
        )
        
        policy = LLMPolicy(
            primary="openai/gpt-4o",
            retry=1,
            fallback=["anthropic/claude-3-5-sonnet-20241022"],
        )
        
        # Mock: OpenAI 실패, Anthropic 성공
        with patch.object(LLMRegistry, 'get') as mock_get:
            mock_openai = Mock()
            mock_openai.is_available.return_value = True
            mock_openai.generate.side_effect = LLMClientError(
                "Rate limit", provider="openai", recoverable=True
            )
            
            mock_anthropic = Mock()
            mock_anthropic.is_available.return_value = True
            mock_anthropic.generate.return_value = Mock(
                content="Hello from Claude",
                model="claude-3-5-sonnet-20241022",
                provider="anthropic",
                tokens_input=10,
                tokens_output=5,
                tokens_total=15,
                latency_ms=100,
                finish_reason="stop",
                attempt=1,
                fallback_from=None,
            )
            
            def side_effect(provider):
                if provider == "openai":
                    return mock_openai
                return mock_anthropic
            
            mock_get.side_effect = side_effect
            
            router = LLMRouter(policy=policy, agent_id="test")
            messages = [LLMMessage(role="user", content="Hi")]
            
            response = router.route(messages)
            
            assert response.provider == "anthropic"
            assert len(router.attempts) >= 2


class TestLLMRouterAllFailed:
    """LLM Router 전체 실패 시나리오"""
    
    def test_router_all_providers_failed(self):
        """모든 Provider 실패"""
        from nexous.llm import (
            LLMRouter, LLMPolicy, LLMMessage,
            LLMClientError, LLMAllProvidersFailedError, LLMRegistry
        )
        
        policy = LLMPolicy(
            primary="openai/gpt-4o",
            retry=1,
            fallback=["anthropic/claude-3-5-sonnet-20241022"],
        )
        
        # Mock: 모든 Provider 실패
        with patch.object(LLMRegistry, 'get') as mock_get:
            mock_client = Mock()
            mock_client.is_available.return_value = True
            mock_client.generate.side_effect = LLMClientError(
                "API Error", provider="any", recoverable=False
            )
            mock_get.return_value = mock_client
            
            router = LLMRouter(policy=policy, agent_id="test")
            messages = [LLMMessage(role="user", content="Hi")]
            
            with pytest.raises(LLMAllProvidersFailedError) as exc_info:
                router.route(messages)
            
            assert len(exc_info.value.attempts) >= 2
    
    def test_router_all_failed_trace(self):
        """전체 실패 시 Trace 기록"""
        from nexous.llm import (
            LLMRouter, LLMPolicy, LLMMessage,
            LLMClientError, LLMAllProvidersFailedError, LLMRegistry
        )
        
        policy = LLMPolicy(
            primary="openai/gpt-4o",
            retry=1,
            fallback=[],
        )
        
        trace_calls = []
        def mock_trace(**kwargs):
            trace_calls.append(kwargs)
        
        with patch.object(LLMRegistry, 'get') as mock_get:
            mock_client = Mock()
            mock_client.is_available.return_value = True
            mock_client.generate.side_effect = LLMClientError(
                "API Error", provider="openai", recoverable=False
            )
            mock_get.return_value = mock_client
            
            router = LLMRouter(
                policy=policy,
                trace_callback=mock_trace,
                agent_id="test_agent",
            )
            messages = [LLMMessage(role="user", content="Hi")]
            
            with pytest.raises(LLMAllProvidersFailedError):
                router.route(messages)
            
            # ERROR trace 기록 확인
            error_traces = [t for t in trace_calls if t.get("status") == "ERROR"]
            assert len(error_traces) >= 1


class TestGenericAgentWithRouter:
    """GenericAgent + Router 통합 테스트"""
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY", "").startswith("sk-"),
        reason="OPENAI_API_KEY not set"
    )
    def test_agent_uses_router(self):
        """Agent가 Router를 사용하는지 확인"""
        from nexous.core import GenericAgent
        
        agent = GenericAgent(
            agent_id="test_agent",
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
        
        result = agent.execute({"inputs": {"task": "Say hi"}})
        
        assert result["status"] == "success"
        assert result["provider"] == "openai"
        assert "routing_info" in result
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY", "").startswith("sk-"),
        reason="OPENAI_API_KEY not set"
    )
    def test_agent_json_output_validation(self):
        """Agent JSON 출력 검증"""
        from nexous.core import GenericAgent
        
        agent = GenericAgent(
            agent_id="json_agent",
            role="tester",
            purpose="JSON 응답 생성",
            llm_config={
                "policy": {"primary": "openai/gpt-4o", "retry": 1}
            },
            tools=[],
            system_prompt="반드시 JSON 형식으로 응답하세요.",
            output_policy={
                "format": "json",
                "required_fields": ["result"],
            },
        )
        
        result = agent.execute({
            "inputs": {"task": '{"result": "hello"} 형식으로 응답하세요'}
        })
        
        assert result["status"] == "success"
        # validated_output이 있을 수 있음
