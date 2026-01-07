"""
NEXOUS Factory - Agent Factory

Agent 인스턴스를 생성합니다.

플랫폼 책임:
- Agent 정의(템플릿)로부터 인스턴스 생성
- LLM 바인딩
- Tool 바인딩
- 설정 적용

주의: Factory는 Agent를 "생성"만 합니다.
생성된 Agent가 "무엇을 하는가"는 Factory의 관심사가 아닙니다.
"""

from typing import Any, Callable, Dict, List, Optional, Type
from pathlib import Path
import yaml
import logging

from nexous.core.registry import AgentRegistry, AgentInfo, AgentCategory, AgentRole, get_registry
from nexous.core.lifecycle import LifecycleManager, AgentState, get_lifecycle_manager

logger = logging.getLogger(__name__)


class AgentInstance:
    """
    생성된 Agent 인스턴스 (플랫폼이 관리하는 래퍼)
    
    이것은 플랫폼이 생성한 Agent 인스턴스를 감싸는 래퍼입니다.
    실제 작업은 내부의 _agent가 수행합니다.
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_info: AgentInfo,
        llm: Any,
        tools: List[Any] = None,
        inner_agent: Any = None,
    ):
        self.agent_id = agent_id
        self.info = agent_info
        self.llm = llm
        self.tools = tools or []
        self._agent = inner_agent  # 실제 작업 수행 객체
        
    @property
    def name(self) -> str:
        return self.info.name
    
    @property
    def role(self) -> AgentRole:
        return self.info.role
    
    def invoke(self, input_data: Any) -> Any:
        """Agent 실행 (실제 작업은 _agent가 수행)"""
        if self._agent is None:
            raise ValueError("Inner agent not initialized")
        
        if hasattr(self._agent, 'invoke'):
            return self._agent.invoke(input_data)
        elif callable(self._agent):
            return self._agent(input_data)
        else:
            raise ValueError("Inner agent is not callable")
    
    async def ainvoke(self, input_data: Any) -> Any:
        """비동기 Agent 실행"""
        if self._agent is None:
            raise ValueError("Inner agent not initialized")
        
        if hasattr(self._agent, 'ainvoke'):
            return await self._agent.ainvoke(input_data)
        else:
            return self.invoke(input_data)


class AgentFactory:
    """
    Agent Factory (NEXOUS 플랫폼 핵심)
    
    Agent 정의(템플릿)로부터 실제 인스턴스를 생성합니다.
    생성된 인스턴스는 Lifecycle Manager에 등록됩니다.
    """
    
    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
        lifecycle: Optional[LifecycleManager] = None,
        templates_dir: Optional[Path] = None,
    ):
        self._registry = registry or get_registry()
        self._lifecycle = lifecycle or get_lifecycle_manager()
        self._templates_dir = templates_dir
        
        # LLM 팩토리 (나중에 providers에서 가져옴)
        self._llm_factory = None
        
        # 생성된 인스턴스 캐시
        self._instances: Dict[str, AgentInstance] = {}
        
        logger.info("[NEXOUS] AgentFactory initialized")
    
    def set_llm_factory(self, llm_factory: Any) -> None:
        """LLM Factory 설정"""
        self._llm_factory = llm_factory
    
    def create(
        self,
        agent_name: str,
        project_id: Optional[str] = None,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        tools: Optional[List[Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> AgentInstance:
        """
        Agent 인스턴스 생성
        
        Args:
            agent_name: 등록된 Agent 이름
            project_id: 프로젝트 ID (선택)
            llm_provider: LLM 프로바이더 오버라이드
            llm_model: LLM 모델 오버라이드
            tools: 추가 Tool 목록
            config: 추가 설정
        
        Returns:
            생성된 AgentInstance
        """
        # 1. Registry에서 Agent 정의 조회
        info = self._registry.get(agent_name)
        if info is None:
            raise ValueError(f"Agent not found in registry: {agent_name}")
        
        # 2. Agent ID 생성
        agent_id = f"{project_id}_{agent_name}" if project_id else agent_name
        
        # 3. LLM 생성
        provider = llm_provider or info.default_provider
        model = llm_model or info.default_model
        llm = self._create_llm(provider, model, info.default_temperature)
        
        # 4. 내부 Agent 생성 (팩토리 함수 사용)
        factory_fn = self._registry.get_factory(agent_name)
        inner_agent = None
        if factory_fn:
            inner_agent = factory_fn(
                llm=llm,
                tools=tools,
                config=config or {},
            )
        
        # 5. AgentInstance 생성
        instance = AgentInstance(
            agent_id=agent_id,
            agent_info=info,
            llm=llm,
            tools=tools or [],
            inner_agent=inner_agent,
        )
        
        # 6. Lifecycle에 등록
        self._lifecycle.register_agent(agent_id)
        self._lifecycle.transition_agent(agent_id, AgentState.INITIALIZED)
        
        # 7. 캐시 저장
        self._instances[agent_id] = instance
        
        logger.info(f"[NEXOUS] Agent created: {agent_id} ({provider}/{model})")
        return instance
    
    def create_from_template(
        self,
        template_path: str,
        project_id: Optional[str] = None,
    ) -> AgentInstance:
        """
        템플릿 파일로부터 Agent 생성
        
        Args:
            template_path: YAML 템플릿 경로
            project_id: 프로젝트 ID
        
        Returns:
            생성된 AgentInstance
        """
        path = Path(template_path)
        if not path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            template = yaml.safe_load(f)
        
        # 템플릿에서 정보 추출
        agent_name = template.get('name')
        if not agent_name:
            raise ValueError("Template must have 'name' field")
        
        # 동적으로 Registry에 등록 (임시)
        if not self._registry.exists(agent_name):
            info = AgentInfo(
                name=agent_name,
                display_name=template.get('display_name', agent_name),
                description=template.get('description', ''),
                category=AgentCategory(template.get('category', 'custom')),
                role=AgentRole(template.get('role', 'meta')),
                default_provider=template.get('llm', {}).get('provider', 'anthropic'),
                default_model=template.get('llm', {}).get('model'),
                default_temperature=template.get('llm', {}).get('temperature', 0.7),
                required_tools=template.get('tools', []),
                template_path=str(path),
            )
            self._registry.register(info)
        
        return self.create(
            agent_name=agent_name,
            project_id=project_id,
            config=template.get('config', {}),
        )
    
    def create_project_agents(
        self,
        project_id: str,
        agent_names: List[str],
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, AgentInstance]:
        """
        프로젝트에 필요한 모든 Agent 생성
        
        Args:
            project_id: 프로젝트 ID
            agent_names: 생성할 Agent 이름 목록
            config: 공통 설정
        
        Returns:
            {agent_name: AgentInstance} 딕셔너리
        """
        # 의존성 순서로 정렬
        ordered = self._registry.resolve_order(agent_names)
        
        agents = {}
        for name in ordered:
            try:
                instance = self.create(
                    agent_name=name,
                    project_id=project_id,
                    config=config,
                )
                agents[name] = instance
            except Exception as e:
                logger.error(f"[NEXOUS] Failed to create agent {name}: {e}")
        
        logger.info(f"[NEXOUS] Project agents created: {project_id} ({len(agents)} agents)")
        return agents
    
    def get_instance(self, agent_id: str) -> Optional[AgentInstance]:
        """캐시된 인스턴스 조회"""
        return self._instances.get(agent_id)
    
    def destroy(self, agent_id: str) -> bool:
        """Agent 인스턴스 제거"""
        if agent_id in self._instances:
            self._lifecycle.transition_agent(agent_id, AgentState.TERMINATED)
            self._lifecycle.unregister_agent(agent_id)
            del self._instances[agent_id]
            logger.info(f"[NEXOUS] Agent destroyed: {agent_id}")
            return True
        return False
    
    def destroy_project_agents(self, project_id: str) -> int:
        """프로젝트의 모든 Agent 제거"""
        to_remove = [aid for aid in self._instances if aid.startswith(f"{project_id}_")]
        for agent_id in to_remove:
            self.destroy(agent_id)
        return len(to_remove)
    
    def _create_llm(self, provider: str, model: Optional[str], temperature: float) -> Any:
        """LLM 인스턴스 생성"""
        if self._llm_factory:
            return self._llm_factory.create(provider, model, temperature)
        
        # 기본 LLM 생성 (LangChain 직접 사용)
        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=model or "claude-sonnet-4-20250514",
                temperature=temperature,
            )
        elif provider == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=model or "gpt-4o-mini",
                temperature=temperature,
            )
        elif provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=model or "gemini-2.0-flash",
                temperature=temperature,
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def list_instances(self) -> List[str]:
        """생성된 인스턴스 목록"""
        return list(self._instances.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """Factory 통계"""
        return {
            "total_instances": len(self._instances),
            "by_role": {},  # TODO: 역할별 통계
        }


# 싱글톤 인스턴스
_agent_factory: Optional[AgentFactory] = None

def get_agent_factory() -> AgentFactory:
    """전역 AgentFactory 반환"""
    global _agent_factory
    if _agent_factory is None:
        _agent_factory = AgentFactory()
    return _agent_factory
