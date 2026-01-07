"""
NEXOUS Core - Agent Registry

Agent 정의를 등록하고 관리합니다.

플랫폼 책임:
- Agent 정의(스키마) 등록
- Agent 메타데이터 관리
- Agent 팩토리 함수 매핑
- Agent 의존성 관리

주의: Registry는 Agent "정의"만 관리합니다.
실제 인스턴스 생성은 Factory의 책임입니다.
"""

from typing import Any, Callable, Dict, List, Optional, Type
from enum import Enum
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class AgentCategory(str, Enum):
    """Agent 카테고리"""
    CORE = "core"           # 핵심 (Planner, Executor, Writer, QA)
    DOMAIN = "domain"       # 도메인 전문 (SWMM, GIS, etc.)
    UTILITY = "utility"     # 유틸리티
    CUSTOM = "custom"       # 사용자 정의


class AgentRole(str, Enum):
    """Agent 역할"""
    PLANNER = "planner"     # 계획 수립
    EXECUTOR = "executor"   # 실행
    WRITER = "writer"       # 문서 작성
    QA = "qa"               # 품질 검증
    META = "meta"           # 메타 (오케스트레이션)


class AgentInfo(BaseModel):
    """
    Agent 정의 정보 (플랫폼이 관리하는 스키마)
    
    이것은 Agent "인스턴스"가 아니라 Agent "정의"입니다.
    실제 작업은 이 정의를 바탕으로 생성된 인스턴스가 수행합니다.
    """
    # 식별
    name: str = Field(description="고유 식별자")
    display_name: str = Field(description="표시 이름")
    description: str = Field(description="설명")
    
    # 분류
    category: AgentCategory = Field(default=AgentCategory.CORE)
    role: AgentRole = Field(default=AgentRole.META)
    
    # LLM 설정
    default_provider: str = Field(default="anthropic")
    supported_providers: List[str] = Field(default_factory=lambda: ["anthropic", "openai", "google"])
    default_model: Optional[str] = Field(default=None)
    default_temperature: float = Field(default=0.7)
    
    # 스키마
    input_schema: Optional[Dict[str, Any]] = Field(default=None)
    output_schema: Optional[Dict[str, Any]] = Field(default=None)
    
    # 의존성
    dependencies: List[str] = Field(default_factory=list)
    required_tools: List[str] = Field(default_factory=list)
    
    # 메타데이터
    version: str = Field(default="1.0.0")
    author: Optional[str] = Field(default=None)
    tags: List[str] = Field(default_factory=list)
    
    # 템플릿 경로 (YAML/JSON 정의 파일)
    template_path: Optional[str] = Field(default=None)


class AgentRegistry:
    """
    Agent Registry (NEXOUS 플랫폼 핵심)
    
    Agent 정의를 등록하고 관리합니다.
    Registry는 "무엇이 존재하는가"만 알고,
    "어떻게 생성하는가"는 Factory가 담당합니다.
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
        logger.info("[NEXOUS] AgentRegistry initialized")
    
    def register(self, info: AgentInfo, factory: Optional[Callable] = None) -> None:
        """
        Agent 정의 등록
        
        Args:
            info: Agent 정보
            factory: 인스턴스 생성 함수 (선택)
        """
        self._agents[info.name] = info
        if factory:
            self._factories[info.name] = factory
        logger.info(f"[NEXOUS] Agent registered: {info.name} ({info.category.value})")
    
    def unregister(self, name: str) -> bool:
        """Agent 정의 해제"""
        if name in self._agents:
            del self._agents[name]
            self._factories.pop(name, None)
            logger.info(f"[NEXOUS] Agent unregistered: {name}")
            return True
        return False
    
    def get(self, name: str) -> Optional[AgentInfo]:
        """Agent 정의 조회"""
        return self._agents.get(name)
    
    def get_factory(self, name: str) -> Optional[Callable]:
        """Agent 팩토리 함수 조회"""
        return self._factories.get(name)
    
    def exists(self, name: str) -> bool:
        """Agent 존재 여부"""
        return name in self._agents
    
    def list_all(self) -> List[AgentInfo]:
        """전체 Agent 목록"""
        return list(self._agents.values())
    
    def list_by_category(self, category: AgentCategory) -> List[AgentInfo]:
        """카테고리별 목록"""
        return [a for a in self._agents.values() if a.category == category]
    
    def list_by_role(self, role: AgentRole) -> List[AgentInfo]:
        """역할별 목록"""
        return [a for a in self._agents.values() if a.role == role]
    
    def list_by_tag(self, tag: str) -> List[AgentInfo]:
        """태그별 목록"""
        return [a for a in self._agents.values() if tag in a.tags]
    
    def get_dependencies(self, name: str) -> List[str]:
        """Agent 의존성 조회"""
        info = self.get(name)
        return info.dependencies if info else []
    
    def resolve_order(self, agent_names: List[str]) -> List[str]:
        """의존성 기반 실행 순서 결정 (위상 정렬)"""
        ordered = []
        visited = set()
        
        def visit(name: str):
            if name in visited:
                return
            visited.add(name)
            for dep in self.get_dependencies(name):
                if dep in agent_names:
                    visit(dep)
            ordered.append(name)
        
        for name in agent_names:
            visit(name)
        
        return ordered
    
    def get_stats(self) -> Dict[str, Any]:
        """Registry 통계"""
        return {
            "total": len(self._agents),
            "by_category": {
                cat.value: len(self.list_by_category(cat))
                for cat in AgentCategory
            },
            "by_role": {
                role.value: len(self.list_by_role(role))
                for role in AgentRole
            },
            "with_factory": len(self._factories),
        }


# 싱글톤 인스턴스
def get_registry() -> AgentRegistry:
    """전역 AgentRegistry 반환"""
    return AgentRegistry()
