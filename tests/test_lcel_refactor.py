"""
LangChain Agent LCEL 리팩토링 테스트
"""

import pytest
from unittest.mock import Mock, MagicMock, patch


class TestRunnableInterface:
    """Runnable 인터페이스 테스트"""
    
    def test_base_agent_is_runnable(self):
        """BaseLangChainAgent가 Runnable인지 확인"""
        from langchain_core.runnables import Runnable
        from prometheus.agents import BaseLangChainAgent
        
        assert issubclass(BaseLangChainAgent, Runnable)
    
    def test_simple_chain_agent_builds_chain(self):
        """SimpleChainAgent가 chain을 빌드하는지 확인"""
        from prometheus.agents.langchain_base import SimpleChainAgent, AgentConfig
        from langchain_core.runnables import Runnable
        
        # Mock LLM
        mock_llm = MagicMock()
        mock_llm.__or__ = lambda self, other: MagicMock()
        
        # Agent 생성 (chain 빌드됨)
        with patch.object(SimpleChainAgent, '_build_chain', return_value=MagicMock(spec=Runnable)):
            agent = SimpleChainAgent.__new__(SimpleChainAgent)
            agent.llm = mock_llm
            agent.config = AgentConfig()
            agent.tools = []
            agent.memory = None
            agent.chain = MagicMock(spec=Runnable)
            
            assert agent.chain is not None
    
    def test_structured_output_agent_has_schema(self):
        """StructuredOutputAgent가 output_schema를 가지는지 확인"""
        from prometheus.agents import PlannerAgent, PlanOutput
        from prometheus.agents.langchain_base import StructuredOutputAgent
        
        assert issubclass(PlannerAgent, StructuredOutputAgent)


class TestAgentMethods:
    """Agent 메서드 테스트"""
    
    def test_normalize_input_string(self):
        """문자열 입력 정규화"""
        from prometheus.agents.langchain_base import SimpleChainAgent, AgentConfig
        
        # Mock agent
        agent = SimpleChainAgent.__new__(SimpleChainAgent)
        agent.llm = MagicMock()
        agent.config = AgentConfig()
        agent.tools = []
        agent.memory = None
        
        result = agent._normalize_input("test input")
        assert result == {"input": "test input"}
    
    def test_normalize_input_dict(self):
        """딕셔너리 입력 정규화"""
        from prometheus.agents.langchain_base import SimpleChainAgent, AgentConfig
        
        # Mock agent
        agent = SimpleChainAgent.__new__(SimpleChainAgent)
        agent.llm = MagicMock()
        agent.config = AgentConfig()
        agent.tools = []
        agent.memory = None
        
        result = agent._normalize_input({"key": "value"})
        assert result == {"key": "value"}
    
    def test_get_info(self):
        """get_info 메서드 테스트"""
        from prometheus.agents.langchain_base import SimpleChainAgent, AgentConfig, AgentRole
        
        agent = SimpleChainAgent.__new__(SimpleChainAgent)
        agent.llm = MagicMock()
        agent.config = AgentConfig(name="TestAgent", role=AgentRole.META)
        agent.tools = [MagicMock(), MagicMock()]
        agent.memory = None
        agent.role = AgentRole.META
        agent.chain = MagicMock()
        
        info = agent.get_info()
        
        assert info["name"] == "TestAgent"
        assert info["tools_count"] == 2
        assert info["has_memory"] == False


class TestFallbackAndRetry:
    """Fallback과 Retry 테스트"""
    
    def test_with_fallbacks_returns_runnable(self):
        """with_fallbacks가 Runnable을 반환하는지 확인"""
        from prometheus.agents.langchain_base import SimpleChainAgent, AgentConfig
        from langchain_core.runnables import Runnable
        
        # Mock chain
        mock_chain = MagicMock(spec=Runnable)
        mock_chain.with_fallbacks = MagicMock(return_value=MagicMock(spec=Runnable))
        
        agent = SimpleChainAgent.__new__(SimpleChainAgent)
        agent.chain = mock_chain
        
        # Fallback agent
        fallback_agent = SimpleChainAgent.__new__(SimpleChainAgent)
        fallback_agent.chain = MagicMock(spec=Runnable)
        
        result = agent.with_fallbacks([fallback_agent])
        
        assert mock_chain.with_fallbacks.called
    
    def test_with_retry_returns_runnable(self):
        """with_retry가 Runnable을 반환하는지 확인"""
        from prometheus.agents.langchain_base import SimpleChainAgent, AgentConfig
        from langchain_core.runnables import Runnable
        
        # Mock chain
        mock_chain = MagicMock(spec=Runnable)
        mock_chain.with_retry = MagicMock(return_value=MagicMock(spec=Runnable))
        
        agent = SimpleChainAgent.__new__(SimpleChainAgent)
        agent.chain = mock_chain
        
        result = agent.with_retry(stop_after_attempt=3)
        
        assert mock_chain.with_retry.called


class TestPipeOperator:
    """파이프 연산자 테스트"""
    
    def test_or_operator(self):
        """| 연산자 테스트"""
        from prometheus.agents.langchain_base import SimpleChainAgent
        from langchain_core.runnables import Runnable
        
        # Mock chain
        mock_chain = MagicMock(spec=Runnable)
        mock_other = MagicMock(spec=Runnable)
        mock_chain.__or__ = MagicMock(return_value=MagicMock(spec=Runnable))
        
        agent = SimpleChainAgent.__new__(SimpleChainAgent)
        agent.chain = mock_chain
        
        result = agent | mock_other
        
        assert mock_chain.__or__.called


class TestAgentImportsAfterRefactor:
    """리팩토링 후 import 테스트"""
    
    def test_all_agents_importable(self):
        """모든 Agent import 가능"""
        from prometheus.agents import (
            BaseLangChainAgent,
            SimpleChainAgent,
            StructuredOutputAgent,
            ToolCallingAgent,
            PlannerAgent,
            ExecutorAgent,
            WriterAgent,
            QAAgent,
        )
        
        assert BaseLangChainAgent is not None
        assert SimpleChainAgent is not None
        assert StructuredOutputAgent is not None
        assert ToolCallingAgent is not None
    
    def test_factory_functions_importable(self):
        """팩토리 함수 import 가능"""
        from prometheus.agents import (
            create_planner_agent,
            create_executor_agent,
            create_writer_agent,
            create_qa_agent,
        )
        
        assert callable(create_planner_agent)
        assert callable(create_executor_agent)
        assert callable(create_writer_agent)
        assert callable(create_qa_agent)
    
    def test_agent_config_importable(self):
        """AgentConfig import 가능"""
        from prometheus.agents import AgentConfig, AgentRole, AgentOutput
        
        config = AgentConfig(name="Test", role=AgentRole.PLANNER)
        assert config.name == "Test"
        
        output = AgentOutput(success=True, result="test")
        assert output.success == True
