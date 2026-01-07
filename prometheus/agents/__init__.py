"""
PROMETHEUS Agents

LangChain 기반 Multi-Agent 시스템
각 Agent는 특정 역할을 수행합니다.
"""

# LangChain 기반 Agent
from prometheus.agents.langchain_base import (
    BaseLangChainAgent,
    SimpleChainAgent,
    StructuredOutputAgent,
    ToolCallingAgent,
    AgentConfig,
    AgentRole,
    AgentOutput,
)

from prometheus.agents.planner import (
    PlannerAgent,
    PlanOutput,
    PlanStep,
    create_planner_agent,
)

from prometheus.agents.executor import (
    ExecutorAgent,
    ExecutionResult,
    StepResult,
    ToolCallResult,
    create_executor_agent,
    # 기본 Tools
    python_exec,
    file_write,
    file_read,
    web_search,
    rag_search,
    DEFAULT_TOOLS,
)

from prometheus.agents.writer import (
    WriterAgent,
    ReportOutput,
    Citation,
    create_writer_agent,
)

from prometheus.agents.qa import (
    QAAgent,
    QAResult,
    QAIssue,
    create_qa_agent,
)

# 침수 논문 전용 Agent
from prometheus.agents.literature import (
    LiteratureAgent,
    LiteratureReviewOutput,
    PaperInfo,
    create_literature_agent,
)

from prometheus.agents.gis import (
    GISAgent,
    GISAnalysisOutput,
    FloodRiskZone,
    DEMAnalysis,
    create_gis_agent,
)

from prometheus.agents.swmm import (
    SWMMAgent,
    SWMMOutput,
    RainfallEvent,
    SubcatchmentResult,
    NodeResult,
    LIDPerformance,
    create_swmm_agent,
)

from prometheus.agents.visualization import (
    VisualizationAgent,
    VisualizationOutput,
    ChartSpec,
    create_visualization_agent,
)

from prometheus.agents.academic_writer import (
    AcademicWriterAgent,
    AcademicPaperOutput,
    create_academic_writer_agent,
)


__all__ = [
    # Base
    "BaseLangChainAgent",
    "SimpleChainAgent",
    "StructuredOutputAgent",
    "ToolCallingAgent",
    "AgentConfig",
    "AgentRole",
    "AgentOutput",
    
    # Planner
    "PlannerAgent",
    "PlanOutput",
    "PlanStep",
    "create_planner_agent",
    
    # Executor
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
    
    # Writer
    "WriterAgent",
    "ReportOutput",
    "Citation",
    "create_writer_agent",
    
    # QA
    "QAAgent",
    "QAResult",
    "QAIssue",
    "create_qa_agent",
    
    # Literature (문헌 조사)
    "LiteratureAgent",
    "LiteratureReviewOutput",
    "PaperInfo",
    "create_literature_agent",
    
    # GIS (지리 분석)
    "GISAgent",
    "GISAnalysisOutput",
    "FloodRiskZone",
    "DEMAnalysis",
    "create_gis_agent",
    
    # SWMM (침수 시뮬레이션)
    "SWMMAgent",
    "SWMMOutput",
    "RainfallEvent",
    "SubcatchmentResult",
    "NodeResult",
    "LIDPerformance",
    "create_swmm_agent",
    
    # Visualization (시각화)
    "VisualizationAgent",
    "VisualizationOutput",
    "ChartSpec",
    "create_visualization_agent",
    
    # Academic Writer (학술 논문)
    "AcademicWriterAgent",
    "AcademicPaperOutput",
    "create_academic_writer_agent",
]


# =============================================================================
# 편의 함수
# =============================================================================

def create_all_agents(
    planner_provider: str = "anthropic",
    executor_provider: str = "openai",
    writer_provider: str = "google",
    qa_provider: str = "anthropic",
):
    """
    모든 Agent 생성
    
    Args:
        planner_provider: Planner LLM 프로바이더
        executor_provider: Executor LLM 프로바이더
        writer_provider: Writer LLM 프로바이더
        qa_provider: QA LLM 프로바이더
    
    Returns:
        Dict[str, Agent]
    """
    return {
        "planner": create_planner_agent(provider=planner_provider),
        "executor": create_executor_agent(provider=executor_provider),
        "writer": create_writer_agent(provider=writer_provider),
        "qa": create_qa_agent(provider=qa_provider),
    }
