"""
NEXUS Agent Registry

사용 가능한 Agent를 등록하고 관리합니다.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Type
from pydantic import BaseModel, Field
from enum import Enum

from prometheus.agents.langchain_base import BaseLangChainAgent, AgentRole

logger = logging.getLogger(__name__)


class AgentCategory(str, Enum):
    """Agent 카테고리"""
    CORE = "core"           # 핵심 Agent (Planner, Executor, Writer, QA)
    DOMAIN = "domain"       # 도메인 전문 Agent
    UTILITY = "utility"     # 유틸리티 Agent
    CUSTOM = "custom"       # 사용자 정의 Agent


class AgentInfo(BaseModel):
    """Agent 정보"""
    name: str = Field(description="Agent 이름 (고유 식별자)")
    display_name: str = Field(description="표시 이름")
    description: str = Field(description="설명")
    category: AgentCategory = Field(default=AgentCategory.CORE)
    role: AgentRole = Field(default=AgentRole.META)
    
    # 기본 설정
    default_provider: str = Field(default="anthropic", description="기본 LLM 프로바이더")
    supported_providers: List[str] = Field(default_factory=lambda: ["anthropic", "openai", "google"])
    
    # 입출력 스키마
    input_schema: Optional[Dict[str, Any]] = Field(default=None)
    output_schema: Optional[Dict[str, Any]] = Field(default=None)
    
    # 의존성
    dependencies: List[str] = Field(default_factory=list, description="의존하는 다른 Agent")
    
    # 메타데이터
    version: str = Field(default="1.0.0")
    author: Optional[str] = Field(default=None)
    tags: List[str] = Field(default_factory=list)


class AgentRegistry:
    """
    Agent Registry
    
    사용 가능한 모든 Agent를 등록하고 관리합니다.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._agents: Dict[str, AgentInfo] = {}
        self._factories: Dict[str, Callable] = {}
        self._initialized = True
        
        # 기본 Agent 등록
        self._register_core_agents()
        self._register_domain_agents()
    
    def _register_core_agents(self):
        """핵심 Agent 등록"""
        from prometheus.agents import (
            create_planner_agent,
            create_executor_agent,
            create_writer_agent,
            create_qa_agent,
        )
        
        # Planner
        self.register(
            AgentInfo(
                name="planner",
                display_name="Planner Agent",
                description="작업 계획을 수립합니다. 복잡한 요청을 단계별로 분해합니다.",
                category=AgentCategory.CORE,
                role=AgentRole.PLANNER,
                default_provider="anthropic",
                tags=["planning", "task-decomposition"]
            ),
            factory=create_planner_agent
        )
        
        # Executor
        self.register(
            AgentInfo(
                name="executor",
                display_name="Executor Agent",
                description="계획을 실행합니다. 코드 실행, Tool 호출을 담당합니다.",
                category=AgentCategory.CORE,
                role=AgentRole.EXECUTOR,
                default_provider="openai",
                tags=["execution", "tool-calling", "code"]
            ),
            factory=create_executor_agent
        )
        
        # Writer
        self.register(
            AgentInfo(
                name="writer",
                display_name="Writer Agent",
                description="결과를 문서화합니다. 보고서, 요약을 작성합니다.",
                category=AgentCategory.CORE,
                role=AgentRole.WRITER,
                default_provider="google",
                tags=["writing", "documentation", "report"]
            ),
            factory=create_writer_agent
        )
        
        # QA
        self.register(
            AgentInfo(
                name="qa",
                display_name="QA Agent",
                description="결과물을 검증합니다. 품질 평가, 피드백을 제공합니다.",
                category=AgentCategory.CORE,
                role=AgentRole.QA,
                default_provider="anthropic",
                tags=["quality", "review", "validation"]
            ),
            factory=create_qa_agent
        )
    
    def _register_domain_agents(self):
        """도메인 전문 Agent 등록"""
        try:
            from prometheus.agents import (
                create_literature_agent,
                create_gis_agent,
                create_swmm_agent,
                create_visualization_agent,
                create_academic_writer_agent,
            )
            
            # Literature
            self.register(
                AgentInfo(
                    name="literature",
                    display_name="Literature Agent",
                    description="문헌 조사를 수행합니다. 관련 논문을 검색하고 분석합니다.",
                    category=AgentCategory.DOMAIN,
                    role=AgentRole.META,
                    default_provider="anthropic",
                    tags=["literature", "research", "paper"]
                ),
                factory=create_literature_agent
            )
            
            # GIS
            self.register(
                AgentInfo(
                    name="gis",
                    display_name="GIS Agent",
                    description="지리 정보를 분석합니다. DEM, 침수 위험 분석을 수행합니다.",
                    category=AgentCategory.DOMAIN,
                    role=AgentRole.EXECUTOR,
                    default_provider="openai",
                    tags=["gis", "spatial", "flood"]
                ),
                factory=create_gis_agent
            )
            
            # SWMM
            self.register(
                AgentInfo(
                    name="swmm",
                    display_name="SWMM Agent",
                    description="침수 시뮬레이션을 수행합니다. EPA-SWMM 기반 분석.",
                    category=AgentCategory.DOMAIN,
                    role=AgentRole.EXECUTOR,
                    default_provider="openai",
                    dependencies=["gis"],
                    tags=["swmm", "simulation", "flood", "hydrology"]
                ),
                factory=create_swmm_agent
            )
            
            # Visualization
            self.register(
                AgentInfo(
                    name="visualization",
                    display_name="Visualization Agent",
                    description="데이터를 시각화합니다. 그래프, 지도를 생성합니다.",
                    category=AgentCategory.DOMAIN,
                    role=AgentRole.WRITER,
                    default_provider="google",
                    tags=["visualization", "chart", "map"]
                ),
                factory=create_visualization_agent
            )
            
            # Academic Writer
            self.register(
                AgentInfo(
                    name="academic_writer",
                    display_name="Academic Writer Agent",
                    description="학술 논문을 작성합니다. KCI, IEEE 등 형식 지원.",
                    category=AgentCategory.DOMAIN,
                    role=AgentRole.WRITER,
                    default_provider="anthropic",
                    dependencies=["literature"],
                    tags=["academic", "paper", "writing"]
                ),
                factory=create_academic_writer_agent
            )
            
        except ImportError as e:
            logger.warning(f"도메인 Agent 로드 실패: {e}")
    
    def register(
        self,
        info: AgentInfo,
        factory: Callable,
    ) -> None:
        """Agent 등록"""
        self._agents[info.name] = info
        self._factories[info.name] = factory
        logger.debug(f"Agent 등록: {info.name}")
    
    def unregister(self, name: str) -> bool:
        """Agent 등록 해제"""
        if name in self._agents:
            del self._agents[name]
            del self._factories[name]
            return True
        return False
    
    def get(self, name: str) -> Optional[AgentInfo]:
        """Agent 정보 조회"""
        return self._agents.get(name)
    
    def create(
        self,
        name: str,
        provider: Optional[str] = None,
        **kwargs
    ) -> BaseLangChainAgent:
        """Agent 인스턴스 생성"""
        if name not in self._factories:
            raise ValueError(f"Unknown agent: {name}")
        
        info = self._agents[name]
        provider = provider or info.default_provider
        
        return self._factories[name](provider=provider, **kwargs)
    
    def list_all(self) -> List[AgentInfo]:
        """모든 Agent 목록"""
        return list(self._agents.values())
    
    def list_by_category(self, category: AgentCategory) -> List[AgentInfo]:
        """카테고리별 Agent 목록"""
        return [a for a in self._agents.values() if a.category == category]
    
    def list_by_tag(self, tag: str) -> List[AgentInfo]:
        """태그별 Agent 목록"""
        return [a for a in self._agents.values() if tag in a.tags]
    
    def get_dependencies(self, name: str) -> List[str]:
        """Agent 의존성 조회"""
        info = self.get(name)
        if info:
            return info.dependencies
        return []
    
    def resolve_order(self, agent_names: List[str]) -> List[str]:
        """의존성 기반 실행 순서 결정"""
        ordered = []
        visited = set()
        
        def visit(name: str):
            if name in visited:
                return
            visited.add(name)
            
            # 의존성 먼저 방문
            for dep in self.get_dependencies(name):
                if dep in agent_names:
                    visit(dep)
            
            ordered.append(name)
        
        for name in agent_names:
            visit(name)
        
        return ordered


# =============================================================================
# 싱글톤 인스턴스
# =============================================================================

def get_registry() -> AgentRegistry:
    """AgentRegistry 싱글톤 반환"""
    return AgentRegistry()
