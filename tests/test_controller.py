"""
test_controller.py - Controller 모듈 테스트

이 파일의 책임:
- AgentFactory 테스트
- Router 테스트
- LifecycleManager 테스트
- MetaAgent 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any

from prometheus.controller import (
    MetaAgent,
    MetaAgentConfig,
    ExecutionMode,
    ProjectExecutionResult,
    AgentFactory,
    AgentFactoryError,
    Router,
    RouterConfig,
    RouteDecision,
    RoutingStrategy,
    TaskType,
    LifecycleManager,
    LifecycleConfig,
    AgentState,
    ProjectState,
)
from prometheus.config import (
    ProjectConfig,
    ProjectMetadata,
    AgentConfig as ProjAgentConfig,
    AgentType,
    LLMProviderConfig,
    LLMProvider,
)
from prometheus.llm import LLMResponse, TokenUsage


class MockLLMClient:
    """테스트용 Mock LLM"""
    
    def __init__(self, response: str = "Mock response"):
        self.response = response
    
    async def generate(self, messages, **kwargs):
        return LLMResponse(content=self.response, model="mock")
    
    async def generate_with_tools(self, messages, tools, **kwargs):
        return LLMResponse(content=self.response, model="mock")


class TestAgentFactory:
    """AgentFactory 테스트"""
    
    def test_create_agent(self) -> None:
        """Agent 생성"""
        factory = AgentFactory()
        
        agent = factory.create_agent(AgentType.PLANNER)
        
        assert agent.agent_type == "planner"
    
    def test_create_all_agent_types(self) -> None:
        """모든 Agent 타입 생성"""
        factory = AgentFactory()
        
        for agent_type in AgentType:
            agent = factory.create_agent(agent_type)
            assert agent is not None
    
    def test_create_with_llm(self) -> None:
        """LLM과 함께 생성"""
        factory = AgentFactory()
        mock_llm = MockLLMClient()
        
        agent = factory.create_agent(
            AgentType.EXECUTOR,
            llm=mock_llm,
        )
        
        assert agent.llm is mock_llm
    
    def test_create_from_project_config(self) -> None:
        """프로젝트 설정으로부터 생성"""
        factory = AgentFactory()
        
        project_config = ProjectConfig(
            metadata=ProjectMetadata(name="test_project"),
            default_llm=LLMProviderConfig(
                provider=LLMProvider.OPENAI,
                model="gpt-4",
            ),
            agents=[
                ProjAgentConfig(agent_type=AgentType.PLANNER),
            ],
        )
        
        # auto_bind_llm=False로 테스트 (실제 API 키 없이)
        agent = factory.create_from_project_config(
            project_config,
            AgentType.PLANNER,
            auto_bind_llm=False,
        )
        
        assert agent.agent_type == "planner"
    
    def test_tool_registry(self) -> None:
        """Tool 등록"""
        factory = AgentFactory()
        
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        
        factory.register_tool("test_tool", mock_tool)
        
        assert "test_tool" in factory.list_tools()
        assert factory.get_tool("test_tool") is mock_tool
    
    def test_agent_caching(self) -> None:
        """Agent 캐싱"""
        factory = AgentFactory()
        
        agent1 = factory.create_agent(
            AgentType.PLANNER,
            project_id="proj1",
        )
        
        cached = factory.get_cached_agent("proj1", AgentType.PLANNER)
        
        assert cached is agent1
    
    def test_clear_cache(self) -> None:
        """캐시 클리어"""
        factory = AgentFactory()
        
        factory.create_agent(AgentType.PLANNER, project_id="proj1")
        factory.create_agent(AgentType.EXECUTOR, project_id="proj1")
        
        factory.clear_cache("proj1")
        
        assert factory.get_cached_agent("proj1", AgentType.PLANNER) is None


class TestRouter:
    """Router 테스트"""
    
    def test_route_sync_planner(self) -> None:
        """동기 라우팅 - Planner"""
        router = Router()
        
        decision = router.route_sync("이 작업의 계획을 세워주세요")
        
        assert decision.target_agent == AgentType.PLANNER
    
    def test_route_sync_executor(self) -> None:
        """동기 라우팅 - Executor"""
        router = Router()
        
        decision = router.route_sync("이 코드를 실행해주세요")
        
        assert decision.target_agent == AgentType.EXECUTOR
    
    def test_route_sync_writer(self) -> None:
        """동기 라우팅 - Writer"""
        router = Router()
        
        decision = router.route_sync("보고서를 작성해주세요")
        
        assert decision.target_agent == AgentType.WRITER
    
    def test_route_sync_qa(self) -> None:
        """동기 라우팅 - QA"""
        router = Router()
        
        decision = router.route_sync("이 결과물을 검토해주세요")
        
        assert decision.target_agent == AgentType.QA
    
    def test_route_sync_fallback(self) -> None:
        """동기 라우팅 - 폴백"""
        router = Router(config=RouterConfig(fallback_agent=AgentType.EXECUTOR))
        
        decision = router.route_sync("random unknown request")
        
        assert decision.target_agent == AgentType.EXECUTOR
    
    @pytest.mark.asyncio
    async def test_route_with_llm(self) -> None:
        """LLM 기반 라우팅"""
        mock_response = '{"task_type": "planning", "target_agent": "planner", "requires_planning": true, "confidence": 0.9, "reasoning": "Complex task"}'
        
        router = Router()
        router.bind_llm(MockLLMClient(response=mock_response))
        
        decision = await router.route("복잡한 프로젝트를 시작합니다")
        
        assert decision.target_agent == AgentType.PLANNER
        assert decision.requires_planning is True
    
    def test_add_routing_rule(self) -> None:
        """라우팅 규칙 추가"""
        router = Router()
        
        router.add_routing_rule("커스텀", AgentType.WRITER)
        
        decision = router.route_sync("커스텀 작업 요청")
        assert decision.target_agent == AgentType.WRITER
    
    def test_requires_planning(self) -> None:
        """계획 필요 여부"""
        router = Router(config=RouterConfig(planning_threshold=10))
        
        short_decision = router.route_sync("짧은")
        long_decision = router.route_sync("이것은 매우 긴 요청입니다 " * 10)
        
        assert short_decision.requires_planning is False
        assert long_decision.requires_planning is True


class TestLifecycleManager:
    """LifecycleManager 테스트"""
    
    def test_register_agent(self) -> None:
        """Agent 등록"""
        manager = LifecycleManager()
        
        manager.register_agent("agent_1")
        
        assert manager.get_agent_state("agent_1") == AgentState.CREATED
    
    def test_agent_transition(self) -> None:
        """Agent 상태 전이"""
        manager = LifecycleManager()
        manager.register_agent("agent_1")
        
        # created -> initialized
        result = manager.transition_agent("agent_1", AgentState.INITIALIZED)
        assert result is True
        assert manager.get_agent_state("agent_1") == AgentState.INITIALIZED
        
        # initialized -> idle
        result = manager.transition_agent("agent_1", AgentState.IDLE)
        assert result is True
        
        # idle -> running
        result = manager.transition_agent("agent_1", AgentState.RUNNING)
        assert result is True
    
    def test_invalid_transition(self) -> None:
        """잘못된 상태 전이"""
        manager = LifecycleManager(config=LifecycleConfig(strict_transitions=True))
        manager.register_agent("agent_1")
        
        # created -> running (invalid)
        result = manager.transition_agent("agent_1", AgentState.RUNNING)
        assert result is False
    
    def test_register_project(self) -> None:
        """Project 등록"""
        manager = LifecycleManager()
        
        manager.register_project("project_1")
        
        assert manager.get_project_state("project_1") == ProjectState.CREATED
    
    def test_project_transition(self) -> None:
        """Project 상태 전이"""
        manager = LifecycleManager()
        manager.register_project("project_1")
        
        manager.transition_project("project_1", ProjectState.LOADING)
        manager.transition_project("project_1", ProjectState.READY)
        manager.transition_project("project_1", ProjectState.RUNNING)
        
        assert manager.get_project_state("project_1") == ProjectState.RUNNING
    
    def test_event_handler(self) -> None:
        """이벤트 핸들러"""
        manager = LifecycleManager()
        events_received = []
        
        def handler(event):
            events_received.append(event)
        
        manager.on("agent_registered", handler)
        manager.register_agent("agent_1")
        
        assert len(events_received) == 1
        assert events_received[0].event_type == "agent_registered"
    
    def test_event_history(self) -> None:
        """이벤트 히스토리"""
        manager = LifecycleManager()
        
        manager.register_agent("agent_1")
        manager.transition_agent("agent_1", AgentState.INITIALIZED)
        
        history = manager.get_event_history(entity_id="agent_1")
        
        assert len(history) >= 2
    
    def test_get_valid_transitions(self) -> None:
        """가능한 전이 목록"""
        manager = LifecycleManager()
        
        valid = manager.get_valid_transitions("agent", "idle")
        
        assert "running" in valid
        assert "terminated" in valid
    
    def test_list_agents_and_projects(self) -> None:
        """등록된 Agent/Project 목록"""
        manager = LifecycleManager()
        
        manager.register_agent("agent_1")
        manager.register_agent("agent_2")
        manager.register_project("project_1")
        
        agents = manager.list_agents()
        projects = manager.list_projects()
        
        assert len(agents) == 2
        assert len(projects) == 1


class TestMetaAgent:
    """MetaAgent 테스트"""
    
    def test_initialization(self) -> None:
        """초기화"""
        meta = MetaAgent()
        
        assert meta.config is not None
        assert meta._agent_factory is not None
        assert meta._router is not None
        assert meta._lifecycle is not None
    
    def test_list_projects(self) -> None:
        """프로젝트 목록"""
        meta = MetaAgent()
        
        projects = meta.list_projects()
        
        assert isinstance(projects, list)
    
    def test_register_tool(self) -> None:
        """Tool 등록"""
        meta = MetaAgent()
        mock_tool = MagicMock()
        
        meta.register_tool("test_tool", mock_tool)
        
        assert "test_tool" in meta._agent_factory.list_tools()
    
    def test_config_options(self) -> None:
        """설정 옵션"""
        config = MetaAgentConfig(
            default_mode=ExecutionMode.PLAN_BASED,
            enable_qa=False,
            max_iterations=100,
        )
        meta = MetaAgent(config=config)
        
        assert meta.config.default_mode == ExecutionMode.PLAN_BASED
        assert meta.config.enable_qa is False
        assert meta.config.max_iterations == 100


class TestIntegration:
    """통합 테스트"""
    
    def test_factory_router_integration(self) -> None:
        """Factory + Router 통합"""
        factory = AgentFactory()
        router = Router()
        
        # 요청 라우팅
        decision = router.route_sync("문서를 작성해주세요")
        
        # 해당 Agent 생성
        agent = factory.create_agent(decision.target_agent)
        
        assert agent.agent_type == "writer"
    
    def test_lifecycle_factory_integration(self) -> None:
        """Lifecycle + Factory 통합"""
        factory = AgentFactory()
        lifecycle = LifecycleManager()
        
        # Agent 생성
        agent = factory.create_agent(AgentType.EXECUTOR, project_id="proj1")
        
        # Lifecycle에 등록
        agent_id = "proj1_executor"
        lifecycle.register_agent(agent_id)
        lifecycle.transition_agent(agent_id, AgentState.INITIALIZED)
        lifecycle.transition_agent(agent_id, AgentState.IDLE)
        
        assert lifecycle.get_agent_state(agent_id) == AgentState.IDLE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
