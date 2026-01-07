"""
NEXOUS Core - Lifecycle Manager

Agent와 Project의 생명주기를 관리합니다.

플랫폼 책임:
- Agent 상태 전이 관리 (CREATED → RUNNING → COMPLETED)
- Project 상태 전이 관리
- 이벤트 발행 및 구독
- 상태 히스토리 관리

주의: 이 모듈은 에이전트의 "실행"이 아닌 "생명주기"만 관리합니다.
실제 작업 수행은 생성된 ProjectAgent의 책임입니다.
"""

from typing import Any, Callable, Dict, List, Optional
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class AgentState(str, Enum):
    """Agent 상태 (플랫폼이 관리)"""
    CREATED = "created"
    INITIALIZED = "initialized"
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


class ProjectState(str, Enum):
    """Project 상태 (플랫폼이 관리)"""
    CREATED = "created"
    LOADING = "loading"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class LifecycleEvent(BaseModel):
    """생명주기 이벤트"""
    event_type: str
    entity_type: str  # "agent" or "project"
    entity_id: str
    from_state: Optional[str] = None
    to_state: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StateTransition(BaseModel):
    """상태 전이 규칙"""
    from_state: str
    to_state: str
    
    def __hash__(self):
        return hash((self.from_state, self.to_state))
    
    def __eq__(self, other):
        if isinstance(other, StateTransition):
            return self.from_state == other.from_state and self.to_state == other.to_state
        return False


# 이벤트 핸들러 타입
EventHandler = Callable[[LifecycleEvent], None]


class LifecycleManager:
    """
    생명주기 관리자 (NEXOUS 플랫폼 핵심)
    
    Agent와 Project의 상태 전이를 관리합니다.
    실제 작업 수행은 하지 않으며, 오직 생명주기만 관리합니다.
    """
    
    # Agent 상태 전이 규칙
    AGENT_TRANSITIONS: List[StateTransition] = [
        StateTransition(from_state="created", to_state="initialized"),
        StateTransition(from_state="initialized", to_state="idle"),
        StateTransition(from_state="idle", to_state="running"),
        StateTransition(from_state="running", to_state="idle"),
        StateTransition(from_state="running", to_state="paused"),
        StateTransition(from_state="running", to_state="completed"),
        StateTransition(from_state="running", to_state="failed"),
        StateTransition(from_state="paused", to_state="running"),
        StateTransition(from_state="paused", to_state="terminated"),
        StateTransition(from_state="idle", to_state="terminated"),
        StateTransition(from_state="completed", to_state="idle"),
        StateTransition(from_state="failed", to_state="idle"),
    ]
    
    # Project 상태 전이 규칙
    PROJECT_TRANSITIONS: List[StateTransition] = [
        StateTransition(from_state="created", to_state="loading"),
        StateTransition(from_state="loading", to_state="ready"),
        StateTransition(from_state="loading", to_state="failed"),
        StateTransition(from_state="ready", to_state="running"),
        StateTransition(from_state="running", to_state="paused"),
        StateTransition(from_state="running", to_state="completed"),
        StateTransition(from_state="running", to_state="failed"),
        StateTransition(from_state="paused", to_state="running"),
        StateTransition(from_state="completed", to_state="archived"),
        StateTransition(from_state="failed", to_state="ready"),
        StateTransition(from_state="ready", to_state="archived"),
    ]
    
    def __init__(self, strict_transitions: bool = True):
        self._agent_states: Dict[str, AgentState] = {}
        self._project_states: Dict[str, ProjectState] = {}
        self._event_handlers: Dict[str, List[EventHandler]] = {}
        self._event_history: List[LifecycleEvent] = []
        self._strict_transitions = strict_transitions
        self._max_history = 1000
    
    # ==================== Agent Lifecycle ====================
    
    def register_agent(self, agent_id: str, initial_state: AgentState = AgentState.CREATED) -> None:
        """Agent 등록 (플랫폼이 에이전트 인스턴스를 추적하기 시작)"""
        self._agent_states[agent_id] = initial_state
        self._emit_event("agent_registered", "agent", agent_id, None, initial_state.value)
        logger.info(f"[NEXOUS] Agent registered: {agent_id}")
    
    def get_agent_state(self, agent_id: str) -> Optional[AgentState]:
        """Agent 상태 조회"""
        return self._agent_states.get(agent_id)
    
    def transition_agent(self, agent_id: str, to_state: AgentState, metadata: Optional[Dict] = None) -> bool:
        """Agent 상태 전이"""
        current = self._agent_states.get(agent_id)
        if current is None:
            logger.warning(f"[NEXOUS] Agent not found: {agent_id}")
            return False
        
        if self._strict_transitions and not self._is_valid_agent_transition(current, to_state):
            logger.warning(f"[NEXOUS] Invalid transition: {current} → {to_state}")
            return False
        
        self._agent_states[agent_id] = to_state
        self._emit_event("agent_state_changed", "agent", agent_id, current.value, to_state.value, metadata)
        logger.debug(f"[NEXOUS] Agent {agent_id}: {current} → {to_state}")
        return True
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Agent 등록 해제"""
        if agent_id in self._agent_states:
            old_state = self._agent_states.pop(agent_id)
            self._emit_event("agent_unregistered", "agent", agent_id, old_state.value, "unregistered")
            logger.info(f"[NEXOUS] Agent unregistered: {agent_id}")
            return True
        return False
    
    def _is_valid_agent_transition(self, from_state: AgentState, to_state: AgentState) -> bool:
        return StateTransition(from_state=from_state.value, to_state=to_state.value) in self.AGENT_TRANSITIONS
    
    # ==================== Project Lifecycle ====================
    
    def register_project(self, project_id: str, initial_state: ProjectState = ProjectState.CREATED) -> None:
        """Project 등록"""
        self._project_states[project_id] = initial_state
        self._emit_event("project_registered", "project", project_id, None, initial_state.value)
        logger.info(f"[NEXOUS] Project registered: {project_id}")
    
    def get_project_state(self, project_id: str) -> Optional[ProjectState]:
        """Project 상태 조회"""
        return self._project_states.get(project_id)
    
    def transition_project(self, project_id: str, to_state: ProjectState, metadata: Optional[Dict] = None) -> bool:
        """Project 상태 전이"""
        current = self._project_states.get(project_id)
        if current is None:
            return False
        
        if self._strict_transitions and not self._is_valid_project_transition(current, to_state):
            return False
        
        self._project_states[project_id] = to_state
        self._emit_event("project_state_changed", "project", project_id, current.value, to_state.value, metadata)
        logger.debug(f"[NEXOUS] Project {project_id}: {current} → {to_state}")
        return True
    
    def _is_valid_project_transition(self, from_state: ProjectState, to_state: ProjectState) -> bool:
        return StateTransition(from_state=from_state.value, to_state=to_state.value) in self.PROJECT_TRANSITIONS
    
    # ==================== Event System ====================
    
    def on(self, event_type: str, handler: EventHandler) -> None:
        """이벤트 핸들러 등록"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    def off(self, event_type: str, handler: Optional[EventHandler] = None) -> None:
        """이벤트 핸들러 해제"""
        if event_type in self._event_handlers:
            if handler:
                self._event_handlers[event_type] = [h for h in self._event_handlers[event_type] if h != handler]
            else:
                self._event_handlers[event_type] = []
    
    def _emit_event(self, event_type: str, entity_type: str, entity_id: str, 
                    from_state: Optional[str], to_state: str, metadata: Optional[Dict] = None) -> None:
        """이벤트 발행"""
        event = LifecycleEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            from_state=from_state,
            to_state=to_state,
            metadata=metadata or {},
        )
        
        # 히스토리 저장
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]
        
        # 핸들러 호출
        for handler in self._event_handlers.get(event_type, []) + self._event_handlers.get("*", []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"[NEXOUS] Event handler error: {e}")
    
    # ==================== Query ====================
    
    def list_agents(self) -> Dict[str, AgentState]:
        """등록된 Agent 목록"""
        return self._agent_states.copy()
    
    def list_projects(self) -> Dict[str, ProjectState]:
        """등록된 Project 목록"""
        return self._project_states.copy()
    
    def get_history(self, entity_id: Optional[str] = None, limit: int = 100) -> List[LifecycleEvent]:
        """이벤트 히스토리 조회"""
        events = self._event_history
        if entity_id:
            events = [e for e in events if e.entity_id == entity_id]
        return events[-limit:]
    
    def reset(self) -> None:
        """전체 초기화"""
        self._agent_states.clear()
        self._project_states.clear()
        self._event_history.clear()


# 싱글톤 인스턴스
_lifecycle_manager: Optional[LifecycleManager] = None

def get_lifecycle_manager() -> LifecycleManager:
    """전역 LifecycleManager 반환"""
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = LifecycleManager()
    return _lifecycle_manager
