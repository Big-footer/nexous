"""
PROMETHEUS - Multi-Agent Orchestration Framework

LangChain + LangGraph 기반 Multi-Agent 시스템
"""

__version__ = "0.2.0"
__author__ = "PROMETHEUS Team"
__description__ = "LangChain-based Multi-Agent Orchestration Framework"

# =============================================================================
# LangChain Agents (새로운 구조)
# =============================================================================
from prometheus.agents import (
    # Base
    BaseLangChainAgent,
    SimpleChainAgent,
    StructuredOutputAgent,
    AgentConfig,
    AgentRole,
    AgentOutput,
    
    # Planner
    PlannerAgent,
    PlanOutput,
    PlanStep,
    create_planner_agent,
    
    # Executor
    ExecutorAgent,
    ExecutionResult,
    StepResult,
    ToolCallResult,
    create_executor_agent,
    python_exec,
    file_write,
    file_read,
    web_search,
    rag_search,
    DEFAULT_TOOLS,
    
    # Writer
    WriterAgent,
    ReportOutput,
    Citation,
    create_writer_agent,
    
    # QA
    QAAgent,
    QAResult,
    QAIssue,
    create_qa_agent,
    
    # Utility
    create_all_agents,
)

# =============================================================================
# LangGraph Workflow
# =============================================================================
from prometheus.graphs import (
    # State
    AgentState,
    create_initial_state,
    
    # Workflow
    create_workflow,
    PrometheusWorkflow,
    run_workflow_cli,
    
    # Nodes
    meta_agent_node,
    planner_node,
    executor_node,
    writer_node,
    qa_node,
)

# =============================================================================
# Export
# =============================================================================
__all__ = [
    # Version
    "__version__",
    "__author__",
    "__description__",
    
    # Agents
    "BaseLangChainAgent",
    "SimpleChainAgent",
    "StructuredOutputAgent",
    "AgentConfig",
    "AgentRole",
    "AgentOutput",
    "PlannerAgent",
    "PlanOutput",
    "PlanStep",
    "create_planner_agent",
    "ExecutorAgent",
    "ExecutionResult",
    "StepResult",
    "ToolCallResult",
    "create_executor_agent",
    "python_exec",
    "file_write",
    "file_read",
    "web_search",
    "rag_search",
    "DEFAULT_TOOLS",
    "WriterAgent",
    "ReportOutput",
    "Citation",
    "create_writer_agent",
    "QAAgent",
    "QAResult",
    "QAIssue",
    "create_qa_agent",
    "create_all_agents",
    
    # Graphs
    "AgentState",
    "create_initial_state",
    "create_workflow",
    "PrometheusWorkflow",
    "run_workflow_cli",
    "meta_agent_node",
    "planner_node",
    "executor_node",
    "writer_node",
    "qa_node",
]
