"""
AgentFactory - Agent 생성 팩토리

이 파일의 책임:
- Agent 인스턴스 생성
- Agent 타입별 설정 적용
- LLM/Tool 자동 바인딩
- 프로젝트 설정 기반 Agent 구성
"""

from typing import Any, Dict, List, Optional, Type
from prometheus.agents.base import BaseAgent, AgentConfig
from prometheus.agents.planner_agent import PlannerAgent, PlannerConfig
from prometheus.agents.executor_agent import ExecutorAgent, ExecutorConfig
from prometheus.agents.writer_agent import WriterAgent, WriterConfig
from prometheus.agents.qa_agent import QAAgent, QAConfig
from prometheus.llm.base import BaseLLMClient
from prometheus.llm.factory import LLMFactory
from prometheus.config.project_schema import (
    ProjectConfig,
    AgentConfig as ProjectAgentConfig,
    AgentType,
    LLMProviderConfig,
)


class AgentFactoryError(Exception):
    """Agent Factory 오류"""
    pass


class AgentFactory:
    """
    Agent 생성 팩토리
    
    프로젝트 설정을 기반으로 Agent를 생성하고 구성합니다.
    LLM과 Tool을 자동으로 바인딩합니다.
    """
    
    # Agent 타입별 클래스 매핑
    AGENT_TYPE_MAP: Dict[AgentType, Type[BaseAgent]] = {
        AgentType.PLANNER: PlannerAgent,
        AgentType.EXECUTOR: ExecutorAgent,
        AgentType.WRITER: WriterAgent,
        AgentType.QA: QAAgent,
    }
    
    # Agent 타입별 Config 클래스 매핑
    CONFIG_TYPE_MAP: Dict[AgentType, Type[AgentConfig]] = {
        AgentType.PLANNER: PlannerConfig,
        AgentType.EXECUTOR: ExecutorConfig,
        AgentType.WRITER: WriterConfig,
        AgentType.QA: QAConfig,
    }
    
    def __init__(
        self,
        llm_factory: Optional[LLMFactory] = None,
    ) -> None:
        """
        AgentFactory 초기화
        
        Args:
            llm_factory: LLM 팩토리 (None이면 새로 생성)
        """
        self._llm_factory = llm_factory or LLMFactory()
        self._tools_registry: Dict[str, Any] = {}
        self._created_agents: Dict[str, BaseAgent] = {}
    
    def create_agent(
        self,
        agent_type: AgentType,
        config: Optional[AgentConfig] = None,
        llm: Optional[BaseLLMClient] = None,
        tools: Optional[List[Any]] = None,
        project_id: Optional[str] = None,
    ) -> BaseAgent:
        """
        Agent 생성
        
        Args:
            agent_type: Agent 타입
            config: Agent 설정 (None이면 기본값)
            llm: LLM 클라이언트 (None이면 바인딩 안함)
            tools: Tool 목록
            project_id: 프로젝트 ID (캐싱용)
            
        Returns:
            생성된 Agent
        """
        # Agent 클래스 조회
        agent_class = self.AGENT_TYPE_MAP.get(agent_type)
        if agent_class is None:
            raise AgentFactoryError(f"Unknown agent type: {agent_type}")
        
        # Config 클래스 조회 및 생성
        if config is None:
            config_class = self.CONFIG_TYPE_MAP.get(agent_type, AgentConfig)
            config = config_class()
        
        # Agent 생성
        agent = agent_class(config=config)
        
        # LLM 바인딩
        if llm is not None:
            agent.bind_llm(llm)
        
        # Tools 바인딩
        if tools:
            agent.bind_tools(tools)
        
        # 캐싱
        if project_id:
            cache_key = f"{project_id}_{agent_type.value}"
            self._created_agents[cache_key] = agent
        
        return agent
    
    def create_from_project_config(
        self,
        project_config: ProjectConfig,
        agent_type: AgentType,
        auto_bind_llm: bool = True,
        auto_bind_tools: bool = True,
    ) -> BaseAgent:
        """
        프로젝트 설정으로부터 Agent 생성
        
        Args:
            project_config: 프로젝트 설정
            agent_type: Agent 타입
            auto_bind_llm: 자동 LLM 바인딩 여부
            auto_bind_tools: 자동 Tool 바인딩 여부
            
        Returns:
            생성된 Agent
        """
        # Agent 설정 조회
        agent_config = project_config.get_agent_config(agent_type)
        
        # Agent Config 생성
        config_class = self.CONFIG_TYPE_MAP.get(agent_type, AgentConfig)
        config_kwargs = {"name": f"{agent_type.value.capitalize()}Agent"}
        
        if agent_config:
            if agent_config.name:
                config_kwargs["name"] = agent_config.name
            if agent_config.system_prompt:
                config_kwargs["system_prompt"] = agent_config.system_prompt
            # 추가 설정 병합
            config_kwargs.update(agent_config.config)
        
        config = config_class(**config_kwargs)
        
        # Agent 생성
        agent = self.create_agent(
            agent_type=agent_type,
            config=config,
            project_id=project_config.metadata.name,
        )
        
        # LLM 바인딩
        if auto_bind_llm:
            llm_config = agent_config.llm if agent_config and agent_config.llm else project_config.default_llm
            llm = self._llm_factory.create_from_config(
                llm_config,
                cache_key=f"{project_config.metadata.name}_{agent_type.value}_llm",
            )
            agent.bind_llm(llm)
        
        # Tools 바인딩
        if auto_bind_tools and agent_config:
            tools = self._get_tools_for_agent(agent_config.tools)
            if tools:
                agent.bind_tools(tools)
        
        return agent
    
    def create_all_agents(
        self,
        project_config: ProjectConfig,
        auto_bind_llm: bool = True,
        auto_bind_tools: bool = True,
    ) -> Dict[AgentType, BaseAgent]:
        """
        프로젝트의 모든 Agent 생성
        
        Args:
            project_config: 프로젝트 설정
            auto_bind_llm: 자동 LLM 바인딩 여부
            auto_bind_tools: 자동 Tool 바인딩 여부
            
        Returns:
            {AgentType: Agent} 딕셔너리
        """
        agents = {}
        
        for agent_config in project_config.agents:
            agent = self.create_from_project_config(
                project_config=project_config,
                agent_type=agent_config.agent_type,
                auto_bind_llm=auto_bind_llm,
                auto_bind_tools=auto_bind_tools,
            )
            agents[agent_config.agent_type] = agent
        
        return agents
    
    def register_tool(
        self,
        name: str,
        tool: Any,
    ) -> None:
        """
        Tool 등록
        
        Args:
            name: Tool 이름
            tool: Tool 인스턴스
        """
        self._tools_registry[name] = tool
    
    def register_tools(
        self,
        tools: Dict[str, Any],
    ) -> None:
        """
        여러 Tool 등록
        
        Args:
            tools: {이름: Tool} 딕셔너리
        """
        self._tools_registry.update(tools)
    
    def get_tool(
        self,
        name: str,
    ) -> Optional[Any]:
        """
        등록된 Tool 조회
        
        Args:
            name: Tool 이름
            
        Returns:
            Tool 또는 None
        """
        return self._tools_registry.get(name)
    
    def list_tools(self) -> List[str]:
        """
        등록된 Tool 목록
        
        Returns:
            Tool 이름 목록
        """
        return list(self._tools_registry.keys())
    
    def get_cached_agent(
        self,
        project_id: str,
        agent_type: AgentType,
    ) -> Optional[BaseAgent]:
        """
        캐시된 Agent 조회
        
        Args:
            project_id: 프로젝트 ID
            agent_type: Agent 타입
            
        Returns:
            Agent 또는 None
        """
        cache_key = f"{project_id}_{agent_type.value}"
        return self._created_agents.get(cache_key)
    
    def clear_cache(
        self,
        project_id: Optional[str] = None,
    ) -> None:
        """
        캐시 클리어
        
        Args:
            project_id: 프로젝트 ID (None이면 전체)
        """
        if project_id:
            keys_to_remove = [
                k for k in self._created_agents.keys()
                if k.startswith(f"{project_id}_")
            ]
            for key in keys_to_remove:
                del self._created_agents[key]
        else:
            self._created_agents.clear()
    
    def _get_tools_for_agent(
        self,
        tool_names: List[str],
    ) -> List[Any]:
        """
        Agent에 필요한 Tool 목록 조회
        
        Args:
            tool_names: Tool 이름 목록
            
        Returns:
            Tool 인스턴스 목록
        """
        tools = []
        for name in tool_names:
            tool = self._tools_registry.get(name)
            if tool:
                tools.append(tool)
        return tools


# 전역 팩토리 인스턴스
_default_factory: Optional[AgentFactory] = None


def get_agent_factory() -> AgentFactory:
    """
    기본 AgentFactory 인스턴스 획득
    
    Returns:
        AgentFactory 인스턴스
    """
    global _default_factory
    if _default_factory is None:
        _default_factory = AgentFactory()
    return _default_factory
