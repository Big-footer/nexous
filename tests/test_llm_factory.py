"""
LLM Factory 및 Fallback 테스트
"""

import pytest
from unittest.mock import Mock, MagicMock, patch


class TestLLMFactory:
    """LLM Factory 테스트"""
    
    def test_imports(self):
        """Import 테스트"""
        from prometheus.llm import (
            LLMProvider,
            LLMConfig,
            AgentLLMConfig,
            LLMFactory,
            create_llm,
            create_llm_with_fallback,
            create_robust_llm,
            get_llm,
        )
        
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.ANTHROPIC.value == "anthropic"
        assert LLMProvider.GOOGLE.value == "google"
    
    def test_llm_config_defaults(self):
        """LLMConfig 기본값 테스트"""
        from prometheus.llm import LLMConfig, LLMProvider
        
        config = LLMConfig(provider=LLMProvider.ANTHROPIC)
        
        assert config.provider == LLMProvider.ANTHROPIC
        assert config.temperature == 0.7
        assert config.max_retries == 3
    
    def test_agent_llm_config(self):
        """AgentLLMConfig 테스트"""
        from prometheus.llm import AgentLLMConfig, LLMProvider
        
        config = AgentLLMConfig()
        
        assert config.planner.provider == LLMProvider.ANTHROPIC
        assert config.executor.provider == LLMProvider.OPENAI
        assert config.writer.provider == LLMProvider.GOOGLE
        assert config.qa.provider == LLMProvider.ANTHROPIC
    
    def test_default_models(self):
        """기본 모델 설정 테스트"""
        from prometheus.llm import DEFAULT_MODELS, LLMProvider
        
        assert LLMProvider.OPENAI in DEFAULT_MODELS
        assert LLMProvider.ANTHROPIC in DEFAULT_MODELS
        assert LLMProvider.GOOGLE in DEFAULT_MODELS
    
    def test_fallback_priority(self):
        """Fallback 우선순위 테스트"""
        from prometheus.llm import FALLBACK_PRIORITY, LLMProvider
        
        # Anthropic 실패 시 OpenAI → Google 순서
        assert FALLBACK_PRIORITY[LLMProvider.ANTHROPIC][0] == LLMProvider.OPENAI
        assert FALLBACK_PRIORITY[LLMProvider.ANTHROPIC][1] == LLMProvider.GOOGLE
        
        # OpenAI 실패 시 Anthropic → Google 순서
        assert FALLBACK_PRIORITY[LLMProvider.OPENAI][0] == LLMProvider.ANTHROPIC


class TestLLMFactoryClass:
    """LLMFactory 클래스 테스트"""
    
    def test_factory_initialization(self):
        """Factory 초기화 테스트"""
        from prometheus.llm import LLMFactory
        
        factory = LLMFactory(
            enable_fallback=True,
            enable_retry=True,
            max_retries=3,
        )
        
        assert factory.enable_fallback == True
        assert factory.enable_retry == True
        assert factory.max_retries == 3
    
    def test_factory_update_config(self):
        """설정 업데이트 테스트"""
        from prometheus.llm import LLMFactory, LLMProvider
        
        factory = LLMFactory()
        
        # Planner를 OpenAI로 변경
        factory.update_config("planner", provider="openai")
        
        assert factory.config.planner.provider == LLMProvider.OPENAI
    
    def test_factory_clear_cache(self):
        """캐시 초기화 테스트"""
        from prometheus.llm import LLMFactory
        
        factory = LLMFactory()
        factory._instances["test"] = Mock()
        
        factory.clear_cache()
        
        assert len(factory._instances) == 0


class TestFallbackChain:
    """Fallback 체인 테스트"""
    
    @patch('langchain_anthropic.ChatAnthropic')
    @patch('langchain_openai.ChatOpenAI')
    def test_create_llm_with_fallback(self, mock_openai, mock_anthropic):
        """create_llm_with_fallback 테스트"""
        from prometheus.llm import create_llm_with_fallback, clear_llm_cache
        
        clear_llm_cache()
        
        # Mock LLM
        mock_anthropic_instance = MagicMock()
        mock_anthropic_instance.with_fallbacks = MagicMock(return_value=MagicMock())
        mock_anthropic.return_value = mock_anthropic_instance
        
        mock_openai_instance = MagicMock()
        mock_openai.return_value = mock_openai_instance
        
        # Fallback LLM 생성
        llm = create_llm_with_fallback("anthropic")
        
        # with_fallbacks가 호출되었는지 확인
        mock_anthropic_instance.with_fallbacks.assert_called_once()
        
        clear_llm_cache()
    
    @patch('langchain_anthropic.ChatAnthropic')
    def test_create_robust_llm(self, mock_anthropic):
        """create_robust_llm 테스트"""
        from prometheus.llm import create_robust_llm, clear_llm_cache
        
        clear_llm_cache()
        
        # Mock LLM
        mock_instance = MagicMock()
        mock_instance.with_fallbacks = MagicMock(return_value=mock_instance)
        mock_instance.with_retry = MagicMock(return_value=mock_instance)
        mock_anthropic.return_value = mock_instance
        
        # Robust LLM 생성 (Fallback 없이)
        llm = create_robust_llm(
            "anthropic",
            max_retries=3,
            with_fallback=False,
        )
        
        # with_retry가 호출되었는지 확인
        mock_instance.with_retry.assert_called_once()
        
        clear_llm_cache()


class TestNodeIntegration:
    """노드 통합 테스트"""
    
    def test_get_node_llm_factory(self):
        """노드용 LLM Factory 테스트"""
        from prometheus.graphs.nodes import get_node_llm_factory, set_node_llm_factory
        from prometheus.llm import LLMFactory
        
        # 커스텀 Factory 설정
        custom_factory = LLMFactory(max_retries=5)
        set_node_llm_factory(custom_factory)
        
        # 반환된 Factory 확인
        factory = get_node_llm_factory()
        assert factory.max_retries == 5
        
        # 초기화
        set_node_llm_factory(None)
    
    def test_nodes_import_factory(self):
        """노드에서 Factory import 테스트"""
        from prometheus.graphs.nodes import (
            get_node_llm_factory,
            set_node_llm_factory,
            create_robust_llm,
        )
        
        assert callable(get_node_llm_factory)
        assert callable(set_node_llm_factory)
        assert callable(create_robust_llm)


class TestCacheManagement:
    """캐시 관리 테스트"""
    
    def test_clear_llm_cache(self):
        """전역 LLM 캐시 초기화 테스트"""
        from prometheus.llm import clear_llm_cache
        from prometheus.llm.factory import _llm_cache
        
        # 캐시에 데이터 추가 (Mock)
        _llm_cache["test_key"] = MagicMock()
        
        # 캐시 초기화
        clear_llm_cache()
        
        # 캐시 비어있는지 확인
        assert len(_llm_cache) == 0
    
    @patch('langchain_openai.ChatOpenAI')
    def test_cache_reuse(self, mock_openai):
        """캐시 재사용 테스트"""
        from prometheus.llm import create_llm, clear_llm_cache
        
        clear_llm_cache()
        
        mock_instance = MagicMock()
        mock_openai.return_value = mock_instance
        
        # 첫 번째 호출
        llm1 = create_llm("openai", use_cache=True)
        
        # 두 번째 호출 (캐시에서 반환)
        llm2 = create_llm("openai", use_cache=True)
        
        # 같은 인스턴스인지 확인
        assert llm1 is llm2
        
        # ChatOpenAI는 한 번만 호출됨
        assert mock_openai.call_count == 1
        
        clear_llm_cache()
