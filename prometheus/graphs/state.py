"""
PROMETHEUS State 스키마

LangGraph 워크플로우에서 사용하는 State 정의
모든 Agent가 이 State를 읽고 업데이트합니다.
"""

from typing import TypedDict, Annotated, Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


class AgentType(str, Enum):
    """Agent 타입"""
    META = "meta"
    PLANNER = "planner"
    EXECUTOR = "executor"
    WRITER = "writer"
    QA = "qa"


class LLMProvider(str, Enum):
    """LLM Provider"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class StepStatus(str, Enum):
    """단계 상태"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


# =============================================================================
# Pydantic 모델 (구조화된 출력)
# =============================================================================

class PlanStep(BaseModel):
    """계획 단계"""
    step_id: int = Field(description="단계 번호")
    action: str = Field(description="수행할 작업")
    tool: Optional[str] = Field(default=None, description="사용할 Tool")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="입력 데이터")
    expected_output: str = Field(default="", description="예상 출력")
    dependencies: List[int] = Field(default_factory=list, description="의존 단계들")


class PlanOutput(BaseModel):
    """Planner Agent 출력"""
    task_summary: str = Field(description="작업 요약")
    steps: List[PlanStep] = Field(description="실행 단계들")
    total_steps: int = Field(description="총 단계 수")
    estimated_time: str = Field(default="unknown", description="예상 소요 시간")
    fallback_plan: Optional[str] = Field(default=None, description="실패 시 대안")


class ToolCall(BaseModel):
    """Tool 호출 기록"""
    tool_name: str = Field(description="Tool 이름")
    arguments: Dict[str, Any] = Field(description="인자")
    result: Any = Field(default=None, description="결과")
    success: bool = Field(default=True, description="성공 여부")
    error: Optional[str] = Field(default=None, description="에러 메시지")
    execution_time: float = Field(default=0.0, description="실행 시간(초)")


class StepResult(BaseModel):
    """단계 실행 결과"""
    step_id: int = Field(description="단계 번호")
    status: StepStatus = Field(description="상태")
    output: Any = Field(default=None, description="출력")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="Tool 호출 기록")
    error: Optional[str] = Field(default=None, description="에러")


class ExecutionResult(BaseModel):
    """Executor Agent 출력"""
    step_results: List[StepResult] = Field(description="각 단계 결과")
    success_count: int = Field(default=0, description="성공 단계 수")
    fail_count: int = Field(default=0, description="실패 단계 수")
    artifacts: List[str] = Field(default_factory=list, description="생성된 산출물 경로")
    total_execution_time: float = Field(default=0.0, description="총 실행 시간")


class Citation(BaseModel):
    """인용/근거"""
    source: str = Field(description="출처")
    content: str = Field(description="인용 내용")
    url: Optional[str] = Field(default=None, description="URL")


class ReportOutput(BaseModel):
    """Writer Agent 출력"""
    title: str = Field(description="보고서 제목")
    summary: str = Field(description="요약")
    content: str = Field(description="본문 (Markdown)")
    conclusions: List[str] = Field(default_factory=list, description="결론")
    citations: List[Citation] = Field(default_factory=list, description="인용")
    word_count: int = Field(default=0, description="단어 수")


class QAIssue(BaseModel):
    """QA 발견 이슈"""
    severity: str = Field(description="심각도 (high/medium/low)")
    category: str = Field(description="카테고리")
    description: str = Field(description="설명")
    suggestion: str = Field(default="", description="개선 제안")


class QAResult(BaseModel):
    """QA Agent 출력"""
    passed: bool = Field(description="통과 여부")
    score: float = Field(description="품질 점수 (0-100)")
    issues: List[QAIssue] = Field(default_factory=list, description="발견된 이슈")
    recommendations: List[str] = Field(default_factory=list, description="권장사항")


class MetaDecision(BaseModel):
    """Meta Agent 결정"""
    selected_agents: List[AgentType] = Field(description="선택된 Agent들")
    llm_assignments: Dict[str, str] = Field(description="Agent별 LLM 할당")
    skip_qa: bool = Field(default=False, description="QA 스킵 여부")
    reasoning: str = Field(description="결정 이유")


# =============================================================================
# LangGraph State (TypedDict)
# =============================================================================

class AgentState(TypedDict):
    """
    PROMETHEUS 워크플로우 State
    
    모든 Agent가 공유하는 중앙 상태입니다.
    각 Agent는 이 State를 읽고 업데이트합니다.
    """
    
    # 대화 기록 (LangGraph 표준)
    messages: Annotated[list, add_messages]
    
    # 요청 정보
    request: str                          # 원본 사용자 요청
    project_name: str                     # 프로젝트 이름
    trace_id: str                         # 추적 ID
    
    # Meta Agent 결정
    meta_decision: Optional[Dict[str, Any]]  # MetaDecision을 dict로
    
    # 각 Agent 출력
    plan: Optional[Dict[str, Any]]        # PlanOutput을 dict로
    execution_result: Optional[Dict[str, Any]]  # ExecutionResult를 dict로
    report: Optional[Dict[str, Any]]      # ReportOutput을 dict로
    qa_result: Optional[Dict[str, Any]]   # QAResult를 dict로
    
    # 현재 상태
    current_agent: str                    # 현재 실행 중인 Agent
    current_step: int                     # 현재 단계
    
    # 에러 처리
    error: Optional[str]                  # 에러 메시지
    retry_count: int                      # 재시도 횟수
    
    # 실행 정보
    start_time: str                       # 시작 시간 (ISO format)
    artifacts_dir: str                    # 산출물 저장 경로


def create_initial_state(
    request: str,
    project_name: str = "unnamed",
    trace_id: Optional[str] = None,
) -> AgentState:
    """
    초기 State 생성
    
    Args:
        request: 사용자 요청
        project_name: 프로젝트 이름
        trace_id: 추적 ID (없으면 자동 생성)
    
    Returns:
        초기 AgentState
    """
    import uuid
    
    if trace_id is None:
        trace_id = str(uuid.uuid4())[:8]
    
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    artifacts_dir = f"runs/{date_str}/{trace_id}"
    
    return AgentState(
        messages=[],
        request=request,
        project_name=project_name,
        trace_id=trace_id,
        meta_decision=None,
        plan=None,
        execution_result=None,
        report=None,
        qa_result=None,
        current_agent="",
        current_step=0,
        error=None,
        retry_count=0,
        start_time=now.isoformat(),
        artifacts_dir=artifacts_dir,
    )
