"""
LifecycleManager - 생명주기 관리

이 파일의 책임:
- Agent/Project 상태 전이 관리
- 이벤트 기반 생명주기
- 상태 검증
- 이벤트 핸들러 등록
"""

from typing import Any, Callable, Dict, List, Optional
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class AgentState(str, Enum):
    """Agent 상태"""
    
    CREATED = "created"
    INITIALIZED = "initialized"
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


class ProjectState(str, Enum):
    """Project 상태"""
    
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
    """상태 전이 정의"""
    
    from_state: str
    to_state: str
    condition: Optional[str] = None
    
    def __hash__(self):
        return hash((self.from_state, self.to_state))
    
    def __eq__(self, other):
        if isinstance(other, StateTransition):
            return self.from_state == other.from_state and self.to_state == other.to_state
        return False


class LifecycleConfig(BaseModel):
    """생명주기 설정"""
    
    enable_events: bool = True
    enable_history: bool = True
    max_history_size: int = 1000
    strict_transitions: bool = True


# 이벤트 핸들러 타입
EventHandler = Callable[[LifecycleEvent], None]


class LifecycleManager:
    """
    생명주기 관리자
    
    Agent와 Project의 상태 전이를 관리하고
    이벤트 기반 생명주기를 제공합니다.
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
    
    def __init__(
        self,
        config: Optional[LifecycleConfig] = None,
    ) -> None:
        """
        LifecycleManager 초기화
        
        Args:
            config: 생명주기 설정
        """
        self.config = config or LifecycleConfig()
        
        # 상태 저장소
        self._agent_states: Dict[str, AgentState] = {}
        self._project_states: Dict[str, ProjectState] = {}
        
        # 이벤트 핸들러
        self._event_handlers: Dict[str, List[EventHandler]] = {}
        
        # 이벤트 히스토리
        self._event_history: List[LifecycleEvent] = []
    
    # ==================== Agent 상태 관리 ====================
    
    def register_agent(
        self,
        agent_id: str,
        initial_state: AgentState = AgentState.CREATED,
    ) -> None:
        """
        Agent 등록
        
        Args:
            agent_id: Agent ID
            initial_state: 초기 상태
        """
        self._agent_states[agent_id] = initial_state
        self._emit_event(
            event_type="agent_registered",
            entity_type="agent",
            entity_id=agent_id,
            to_state=initial_state.value,
        )
    
    def get_agent_state(
        self,
        agent_id: str,
    ) -> Optional[AgentState]:
        """
        Agent 상태 조회
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent 상태 또는 None
        """
        return self._agent_states.get(agent_id)
    
    def transition_agent(
        self,
        agent_id: str,
        to_state: AgentState,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Agent 상태 전이
        
        Args:
            agent_id: Agent ID
            to_state: 목표 상태
            metadata: 메타데이터
            
        Returns:
            전이 성공 여부
        """
        current_state = self._agent_states.get(agent_id)
        if current_state is None:
            return False
        
        # 전이 검증
        if self.config.strict_transitions:
            if not self._is_valid_agent_transition(current_state, to_state):
                return False
        
        # 상태 업데이트
        self._agent_states[agent_id] = to_state
        
        # 이벤트 발생
        self._emit_event(
            event_type="agent_state_changed",
            entity_type="agent",
            entity_id=agent_id,
            from_state=current_state.value,
            to_state=to_state.value,
            metadata=metadata,
        )
        
        return True
    
    def unregister_agent(
        self,
        agent_id: str,
    ) -> bool:
        """
        Agent 등록 해제
        
        Args:
            agent_id: Agent ID
            
        Returns:
            해제 성공 여부
        """
        if agent_id in self._agent_states:
            old_state = self._agent_states[agent_id]
            del self._agent_states[agent_id]
            
            self._emit_event(
                event_type="agent_unregistered",
                entity_type="agent",
                entity_id=agent_id,
                from_state=old_state.value,
                to_state="unregistered",
            )
            return True
        return False
    
    def _is_valid_agent_transition(
        self,
        from_state: AgentState,
        to_state: AgentState,
    ) -> bool:
        """Agent 상태 전이 유효성 검사"""
        transition = StateTransition(
            from_state=from_state.value,
            to_state=to_state.value,
        )
        return transition in self.AGENT_TRANSITIONS
    
    # ==================== Project 상태 관리 ====================
    
    def register_project(
        self,
        project_id: str,
        initial_state: ProjectState = ProjectState.CREATED,
    ) -> None:
        """
        Project 등록
        
        Args:
            project_id: Project ID
            initial_state: 초기 상태
        """
        self._project_states[project_id] = initial_state
        self._emit_event(
            event_type="project_registered",
            entity_type="project",
            entity_id=project_id,
            to_state=initial_state.value,
        )
    
    def get_project_state(
        self,
        project_id: str,
    ) -> Optional[ProjectState]:
        """
        Project 상태 조회
        
        Args:
            project_id: Project ID
            
        Returns:
            Project 상태 또는 None
        """
        return self._project_states.get(project_id)
    
    def transition_project(
        self,
        project_id: str,
        to_state: ProjectState,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Project 상태 전이
        
        Args:
            project_id: Project ID
            to_state: 목표 상태
            metadata: 메타데이터
            
        Returns:
            전이 성공 여부
        """
        current_state = self._project_states.get(project_id)
        if current_state is None:
            return False
        
        # 전이 검증
        if self.config.strict_transitions:
            if not self._is_valid_project_transition(current_state, to_state):
                return False
        
        # 상태 업데이트
        self._project_states[project_id] = to_state
        
        # 이벤트 발생
        self._emit_event(
            event_type="project_state_changed",
            entity_type="project",
            entity_id=project_id,
            from_state=current_state.value,
            to_state=to_state.value,
            metadata=metadata,
        )
        
        return True
    
    def unregister_project(
        self,
        project_id: str,
    ) -> bool:
        """
        Project 등록 해제
        
        Args:
            project_id: Project ID
            
        Returns:
            해제 성공 여부
        """
        if project_id in self._project_states:
            old_state = self._project_states[project_id]
            del self._project_states[project_id]
            
            self._emit_event(
                event_type="project_unregistered",
                entity_type="project",
                entity_id=project_id,
                from_state=old_state.value,
                to_state="unregistered",
            )
            return True
        return False
    
    def _is_valid_project_transition(
        self,
        from_state: ProjectState,
        to_state: ProjectState,
    ) -> bool:
        """Project 상태 전이 유효성 검사"""
        transition = StateTransition(
            from_state=from_state.value,
            to_state=to_state.value,
        )
        return transition in self.PROJECT_TRANSITIONS
    
    # ==================== 이벤트 관리 ====================
    
    def on(
        self,
        event_type: str,
        handler: EventHandler,
    ) -> None:
        """
        이벤트 핸들러 등록
        
        Args:
            event_type: 이벤트 타입
            handler: 핸들러 함수
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    def off(
        self,
        event_type: str,
        handler: Optional[EventHandler] = None,
    ) -> None:
        """
        이벤트 핸들러 해제
        
        Args:
            event_type: 이벤트 타입
            handler: 핸들러 함수 (None이면 전체 해제)
        """
        if event_type in self._event_handlers:
            if handler:
                self._event_handlers[event_type] = [
                    h for h in self._event_handlers[event_type]
                    if h != handler
                ]
            else:
                self._event_handlers[event_type] = []
    
    def _emit_event(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        to_state: str,
        from_state: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        이벤트 발생
        
        Args:
            event_type: 이벤트 타입
            entity_type: 엔티티 타입
            entity_id: 엔티티 ID
            to_state: 목표 상태
            from_state: 이전 상태
            metadata: 메타데이터
        """
        if not self.config.enable_events:
            return
        
        event = LifecycleEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            from_state=from_state,
            to_state=to_state,
            metadata=metadata or {},
        )
        
        # 히스토리 저장
        if self.config.enable_history:
            self._event_history.append(event)
            # 최대 크기 제한
            if len(self._event_history) > self.config.max_history_size:
                self._event_history = self._event_history[-self.config.max_history_size:]
        
        # 핸들러 호출
        handlers = self._event_handlers.get(event_type, [])
        handlers += self._event_handlers.get("*", [])  # 와일드카드 핸들러
        
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                pass  # 핸들러 오류 무시
    
    # ==================== 조회 메서드 ====================
    
    def get_event_history(
        self,
        entity_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[LifecycleEvent]:
        """
        이벤트 히스토리 조회
        
        Args:
            entity_id: 엔티티 ID 필터
            entity_type: 엔티티 타입 필터
            event_type: 이벤트 타입 필터
            limit: 최대 반환 개수
            
        Returns:
            이벤트 목록
        """
        events = self._event_history
        
        if entity_id:
            events = [e for e in events if e.entity_id == entity_id]
        if entity_type:
            events = [e for e in events if e.entity_type == entity_type]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if limit:
            events = events[-limit:]
        
        return events
    
    def list_agents(self) -> Dict[str, AgentState]:
        """등록된 Agent 목록"""
        return self._agent_states.copy()
    
    def list_projects(self) -> Dict[str, ProjectState]:
        """등록된 Project 목록"""
        return self._project_states.copy()
    
    def get_valid_transitions(
        self,
        entity_type: str,
        current_state: str,
    ) -> List[str]:
        """
        현재 상태에서 가능한 전이 목록
        
        Args:
            entity_type: 엔티티 타입 ("agent" or "project")
            current_state: 현재 상태
            
        Returns:
            가능한 목표 상태 목록
        """
        transitions = (
            self.AGENT_TRANSITIONS if entity_type == "agent"
            else self.PROJECT_TRANSITIONS
        )
        
        return [
            t.to_state for t in transitions
            if t.from_state == current_state
        ]
    
    def clear_history(self) -> None:
        """이벤트 히스토리 초기화"""
        self._event_history.clear()
    
    def reset(self) -> None:
        """전체 초기화"""
        self._agent_states.clear()
        self._project_states.clear()
        self._event_history.clear()
        self._event_handlers.clear()
