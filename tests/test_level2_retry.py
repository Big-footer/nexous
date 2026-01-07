"""
NEXOUS Test - LEVEL 2 Retry Attempt 기록 검증

retry 횟수, 지연, 기록 검증
"""

import os
import json
import time
import pytest
from unittest.mock import patch, Mock


class TestRetryAttempts:
    """Retry 시도 기록 검증"""
    
    def test_retry_count_recorded(self, mock_llm_response):
        """Retry 횟수 기록"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage, LLMRegistry, LLMClientError
        
        policy = LLMPolicy(
            primary="openai/gpt-4o",
            retry=3,
            retry_delay=0.01,  # 빠른 테스트
            fallback=[],
        )
        
        # 2번 실패 후 3번째 성공
        call_count = [0]
        
        def mock_generate(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                raise LLMClientError("Rate limit", provider="openai", recoverable=True)
            return mock_llm_response(content="Success on 3rd try")
        
        mock_client = Mock()
        mock_client.provider = "openai"
        mock_client.is_available.return_value = True
        mock_client.generate.side_effect = mock_generate
        
        with patch.object(LLMRegistry, 'get', return_value=mock_client):
            router = LLMRouter(policy=policy, agent_id="test")
            messages = [LLMMessage(role="user", content="Test")]
            
            response = router.route(messages)
            
            # 3번 시도
            assert len(router.attempts) == 3
            assert router.attempts[0]["success"] is False
            assert router.attempts[1]["success"] is False
            assert router.attempts[2]["success"] is True
            
            # 응답 attempt 번호
            assert response.attempt == 3
    
    def test_retry_attempts_contain_error_info(self, mock_failing_client):
        """실패한 시도에 에러 정보 포함"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage, LLMRegistry, LLMAllProvidersFailedError
        
        policy = LLMPolicy(
            primary="openai/gpt-4o",
            retry=2,
            retry_delay=0.01,
            fallback=[],
        )
        
        with patch.object(LLMRegistry, 'get', return_value=mock_failing_client):
            router = LLMRouter(policy=policy, agent_id="test")
            messages = [LLMMessage(role="user", content="Test")]
            
            with pytest.raises(LLMAllProvidersFailedError):
                router.route(messages)
            
            # 모든 시도에 에러 정보 포함
            for attempt in router.attempts:
                assert attempt["success"] is False
                assert "error" in attempt
                assert attempt["recoverable"] is True
    
    def test_retry_stops_on_unrecoverable_error(self, mock_unrecoverable_client):
        """복구 불가능 에러 시 retry 중단"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage, LLMRegistry, LLMAllProvidersFailedError
        
        policy = LLMPolicy(
            primary="openai/gpt-4o",
            retry=5,  # 5번 retry 설정
            retry_delay=0.01,
            fallback=[],
        )
        
        with patch.object(LLMRegistry, 'get', return_value=mock_unrecoverable_client):
            router = LLMRouter(policy=policy, agent_id="test")
            messages = [LLMMessage(role="user", content="Test")]
            
            with pytest.raises(LLMAllProvidersFailedError):
                router.route(messages)
            
            # 복구 불가능하므로 1번만 시도
            assert len(router.attempts) == 1
            assert router.attempts[0]["recoverable"] is False
    
    def test_retry_attempt_numbers(self, mock_llm_response):
        """각 시도의 attempt 번호 검증"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage, LLMRegistry, LLMClientError
        
        policy = LLMPolicy(
            primary="openai/gpt-4o",
            retry=3,
            retry_delay=0.01,
            fallback=[],
        )
        
        call_count = [0]
        
        def mock_generate(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 2:
                raise LLMClientError("Error", provider="openai", recoverable=True)
            return mock_llm_response()
        
        mock_client = Mock()
        mock_client.provider = "openai"
        mock_client.is_available.return_value = True
        mock_client.generate.side_effect = mock_generate
        
        with patch.object(LLMRegistry, 'get', return_value=mock_client):
            router = LLMRouter(policy=policy, agent_id="test")
            messages = [LLMMessage(role="user", content="Test")]
            
            router.route(messages)
            
            # attempt 번호 확인
            assert router.attempts[0]["attempt"] == 1
            assert router.attempts[1]["attempt"] == 2


class TestRetryDelay:
    """Retry 지연 테스트"""
    
    def test_retry_delay_applied(self, mock_llm_response):
        """Retry 지연 적용"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage, LLMRegistry, LLMClientError
        
        policy = LLMPolicy(
            primary="openai/gpt-4o",
            retry=2,
            retry_delay=0.1,  # 0.1초 지연
            fallback=[],
        )
        
        call_count = [0]
        
        def mock_generate(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise LLMClientError("Error", provider="openai", recoverable=True)
            return mock_llm_response()
        
        mock_client = Mock()
        mock_client.provider = "openai"
        mock_client.is_available.return_value = True
        mock_client.generate.side_effect = mock_generate
        
        with patch.object(LLMRegistry, 'get', return_value=mock_client):
            router = LLMRouter(policy=policy, agent_id="test")
            messages = [LLMMessage(role="user", content="Test")]
            
            start = time.time()
            router.route(messages)
            elapsed = time.time() - start
            
            # 최소 0.1초 이상 걸려야 함 (retry_delay)
            assert elapsed >= 0.09  # 약간의 오차 허용


class TestRetryTrace:
    """Retry Trace 기록"""
    
    def test_retry_recorded_in_attempts(self, mock_llm_response):
        """Retry가 attempts에 기록"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage, LLMRegistry, LLMClientError
        
        policy = LLMPolicy(
            primary="openai/gpt-4o",
            retry=3,
            retry_delay=0.01,
            fallback=[],
        )
        
        call_count = [0]
        
        def mock_generate(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                raise LLMClientError("Error", provider="openai", recoverable=True)
            return mock_llm_response()
        
        mock_client = Mock()
        mock_client.provider = "openai"
        mock_client.is_available.return_value = True
        mock_client.generate.side_effect = mock_generate
        
        trace_calls = []
        def mock_trace(**kwargs):
            trace_calls.append(kwargs)
        
        with patch.object(LLMRegistry, 'get', return_value=mock_client):
            router = LLMRouter(
                policy=policy,
                trace_callback=mock_trace,
                agent_id="test",
            )
            messages = [LLMMessage(role="user", content="Test")]
            
            router.route(messages)
            
            # 성공한 trace만 기록 (실패는 attempts에만)
            success_traces = [t for t in trace_calls if t.get("status") == "OK"]
            assert len(success_traces) >= 1
            
            # attempts에는 모든 시도 기록
            assert len(router.attempts) == 3
    
    def test_retry_attempt_in_response(self, mock_llm_response):
        """응답에 attempt 번호 포함"""
        from nexous.llm import LLMRouter, LLMPolicy, LLMMessage, LLMRegistry, LLMClientError
        
        policy = LLMPolicy(
            primary="openai/gpt-4o",
            retry=2,
            retry_delay=0.01,
            fallback=[],
        )
        
        call_count = [0]
        
        def mock_generate(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise LLMClientError("Error", provider="openai", recoverable=True)
            return mock_llm_response()
        
        mock_client = Mock()
        mock_client.provider = "openai"
        mock_client.is_available.return_value = True
        mock_client.generate.side_effect = mock_generate
        
        with patch.object(LLMRegistry, 'get', return_value=mock_client):
            router = LLMRouter(policy=policy, agent_id="test")
            messages = [LLMMessage(role="user", content="Test")]
            
            response = router.route(messages)
            
            # 2번째 시도에서 성공
            assert response.attempt == 2
