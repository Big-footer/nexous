"""
Controller 모듈

PROMETHEUS의 핵심 컨트롤러 정의들을 포함합니다:
- MetaAgent: 최상위 오케스트레이터
- AgentFactory: Agent 생성 팩토리
- Router: 작업 분배/라우팅
- LifecycleManager: 생명주기 관리
"""

from prometheus.controller.meta_agent import (
    MetaAgent,
    MetaAgentConfig,
    ExecutionMode,
    ProjectExecutionResult,
    run_project,
)
from prometheus.controller.agent_factory import (
    AgentFactory,
    AgentFactoryError,
    get_agent_factory,
)
from prometheus.controller.router import (
    Router,
    RouterConfig,
    RouteDecision,
    RoutingStrategy,
    TaskType,
)
from prometheus.controller.lifecycle import (
    LifecycleManager,
    LifecycleConfig,
    LifecycleEvent,
    AgentState,
    ProjectState,
    StateTransition,
)

__all__ = [
    # MetaAgent
    "MetaAgent",
    "MetaAgentConfig",
    "ExecutionMode",
    "ProjectExecutionResult",
    "run_project",
    # AgentFactory
    "AgentFactory",
    "AgentFactoryError",
    "get_agent_factory",
    # Router
    "Router",
    "RouterConfig",
    "RouteDecision",
    "RoutingStrategy",
    "TaskType",
    # Lifecycle
    "LifecycleManager",
    "LifecycleConfig",
    "LifecycleEvent",
    "AgentState",
    "ProjectState",
    "StateTransition",
]
