"""
NEXOUS Trace Store

Trace 저장소 구조:
traces/
 └─ {project_id}/
     └─ {run_id}/
         ├─ trace.json        ← 실행 요약 + 구조
         └─ events.jsonl      ← 상세 이벤트 로그 (스트리밍)

trace.json 스키마 (v1.0):
{
  "trace_version": "1.0",
  "project_id": "flood_analysis_ulsan_001",
  "run_id": "run_20260101_001",
  "status": "COMPLETED",
  "started_at": "2026-01-01T12:01:00Z",
  "ended_at": "2026-01-01T12:07:32Z",
  "duration_ms": 392000,
  "execution": {
    "mode": "sequential",
    "retry_count": 0
  },
  "agents": [...],
  "artifacts": [...],
  "errors": [],
  "summary": {...}
}
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Enums
# ============================================================================

class RunStatus(str, Enum):
    DEFINED = "DEFINED"
    CREATED = "CREATED"
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"


class StepType(str, Enum):
    INPUT = "INPUT"
    LLM = "LLM"
    TOOL = "TOOL"
    OUTPUT = "OUTPUT"


class EventType(str, Enum):
    # Run 레벨
    RUN_START = "RUN_START"
    RUN_COMPLETE = "RUN_COMPLETE"
    RUN_FAILED = "RUN_FAILED"
    RUN_STOPPED = "RUN_STOPPED"
    
    # Agent 레벨
    AGENT_START = "AGENT_START"
    AGENT_COMPLETE = "AGENT_COMPLETE"
    AGENT_FAILED = "AGENT_FAILED"
    
    # Step 레벨
    STEP_START = "STEP_START"
    STEP_COMPLETE = "STEP_COMPLETE"
    
    # 상세
    LLM_CALL = "LLM_CALL"
    LLM_RESPONSE = "LLM_RESPONSE"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"
    
    # 로그
    LOG = "LOG"
    ERROR = "ERROR"


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class TokenUsage:
    """LLM 토큰 사용량"""
    input: int = 0
    output: int = 0
    total: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "input": self.input,
            "output": self.output,
            "total": self.total
        }


@dataclass
class InputStepPayload:
    """INPUT Step payload_summary"""
    context: Optional[List[str]] = None
    previous_results: Optional[List[str]] = None
    
    def to_dict(self) -> Dict:
        result = {}
        if self.context is not None:
            result["context"] = self.context
        if self.previous_results is not None:
            result["previous_results"] = self.previous_results
        return result


@dataclass
class ToolStepPayload:
    """TOOL Step payload_summary"""
    tool_name: Optional[str] = None
    tool_args: Optional[Dict] = None
    tool_result: Optional[str] = None
    
    def to_dict(self) -> Dict:
        result = {}
        if self.tool_name:
            result["tool_name"] = self.tool_name
        if self.tool_args:
            result["tool_args"] = self.tool_args
        if self.tool_result:
            result["tool_result"] = self.tool_result
        return result


@dataclass
class OutputStepPayload:
    """OUTPUT Step payload_summary"""
    output_keys: Optional[List[str]] = None
    artifact_ids: Optional[List[str]] = None
    
    def to_dict(self) -> Dict:
        result = {}
        if self.output_keys is not None:
            result["output_keys"] = self.output_keys
        if self.artifact_ids is not None:
            result["artifact_ids"] = self.artifact_ids
        return result


@dataclass
class TraceStep:
    """
    Trace Step (v1.0 스키마)
    
    타입별 스키마:
    
    INPUT:
    {
      "step_id": "executor_01.input",
      "type": "INPUT",
      "status": "OK",
      "timestamp": "2026-01-01T12:02:10Z",
      "payload_summary": {"context": [...], "previous_results": [...]}
    }
    
    LLM:
    {
      "step_id": "executor_01.llm_01",
      "type": "LLM",
      "provider": "openai",
      "model": "gpt-4o",
      "status": "OK",
      "started_at": "...",
      "ended_at": "...",
      "latency_ms": 7000,
      "tokens": {"input": 3120, "output": 860, "total": 3980},
      "input_summary": "...",
      "output_summary": "..."
    }
    
    TOOL:
    {
      "step_id": "executor_01.tool_python_exec",
      "type": "TOOL",
      "tool_name": "python_exec",
      "status": "OK",
      "started_at": "...",
      "ended_at": "...",
      "latency_ms": 185000,
      "input_summary": "...",
      "output_summary": "..."
    }
    
    OUTPUT:
    {
      "step_id": "executor_01.output",
      "type": "OUTPUT",
      "status": "OK",
      "timestamp": "...",
      "payload_summary": {"output_keys": [...], "artifact_ids": [...]}
    }
    """
    step_id: str
    type: StepType
    status: str = "OK"  # OK, ERROR
    
    # 공통 (INPUT, OUTPUT용 - legacy)
    timestamp: Optional[str] = None
    payload_summary: Optional[Any] = None
    
    # LLM/TOOL 공통
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    latency_ms: Optional[int] = None
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    
    # LLM 전용
    provider: Optional[str] = None  # openai, anthropic, google
    model: Optional[str] = None
    tokens: Optional[TokenUsage] = None
    
    # TOOL 전용
    tool_name: Optional[str] = None
    
    # 에러
    error: Optional[str] = None
    
    # 내부 사용
    agent_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """타입별 스키마로 변환"""
        step_type = self.type.value if isinstance(self.type, StepType) else self.type
        
        result = {
            "step_id": self.step_id,
            "type": step_type,
            "status": self.status,
        }
        
        if step_type == "LLM":
            # LLM 스키마
            if self.provider:
                result["provider"] = self.provider
            if self.model:
                result["model"] = self.model
            if self.started_at:
                result["started_at"] = self.started_at
            if self.ended_at:
                result["ended_at"] = self.ended_at
            if self.latency_ms is not None:
                result["latency_ms"] = self.latency_ms
            if self.tokens:
                result["tokens"] = self.tokens.to_dict()
            if self.input_summary:
                result["input_summary"] = self.input_summary
            if self.output_summary:
                result["output_summary"] = self.output_summary
                
        elif step_type == "TOOL":
            # TOOL 스키마
            if self.tool_name:
                result["tool_name"] = self.tool_name
            if self.started_at:
                result["started_at"] = self.started_at
            if self.ended_at:
                result["ended_at"] = self.ended_at
            if self.latency_ms is not None:
                result["latency_ms"] = self.latency_ms
            if self.input_summary:
                result["input_summary"] = self.input_summary
            if self.output_summary:
                result["output_summary"] = self.output_summary
                
        else:
            # INPUT, OUTPUT 스키마
            if self.timestamp:
                result["timestamp"] = self.timestamp
            if self.payload_summary:
                payload = self.payload_summary.to_dict() if hasattr(self.payload_summary, 'to_dict') else self.payload_summary
                if payload:
                    result["payload_summary"] = payload
        
        if self.error:
            result["error"] = self.error
        
        return result
    
    @classmethod
    def create_input(
        cls,
        agent_id: str,
        timestamp: str,
        context: List[str] = None,
        previous_results: List[str] = None,
        status: str = "OK"
    ) -> "TraceStep":
        """INPUT Step 생성"""
        return cls(
            step_id=f"{agent_id}.input",
            type=StepType.INPUT,
            status=status,
            timestamp=timestamp,
            payload_summary=InputStepPayload(context=context, previous_results=previous_results),
            agent_id=agent_id
        )
    
    @classmethod
    def create_llm(
        cls,
        agent_id: str,
        sequence: int = 1,
        provider: str = "openai",
        model: str = "gpt-4o",
        started_at: str = None,
        ended_at: str = None,
        latency_ms: int = None,
        tokens_input: int = 0,
        tokens_output: int = 0,
        input_summary: str = None,
        output_summary: str = None,
        status: str = "OK"
    ) -> "TraceStep":
        """LLM Step 생성"""
        return cls(
            step_id=f"{agent_id}.llm_{sequence:02d}",
            type=StepType.LLM,
            status=status,
            provider=provider,
            model=model,
            started_at=started_at,
            ended_at=ended_at,
            latency_ms=latency_ms,
            tokens=TokenUsage(
                input=tokens_input,
                output=tokens_output,
                total=tokens_input + tokens_output
            ),
            input_summary=input_summary,
            output_summary=output_summary,
            agent_id=agent_id
        )
    
    @classmethod
    def create_tool(
        cls,
        agent_id: str,
        tool_name: str,
        started_at: str = None,
        ended_at: str = None,
        latency_ms: int = None,
        input_summary: str = None,
        output_summary: str = None,
        status: str = "OK"
    ) -> "TraceStep":
        """TOOL Step 생성 (v1.0 스키마)"""
        return cls(
            step_id=f"{agent_id}.tool_{tool_name}",
            type=StepType.TOOL,
            status=status,
            tool_name=tool_name,
            started_at=started_at,
            ended_at=ended_at,
            latency_ms=latency_ms,
            input_summary=input_summary,
            output_summary=output_summary,
            agent_id=agent_id
        )
    
    @classmethod
    def create_output(
        cls,
        agent_id: str,
        timestamp: str = None,
        output_keys: List[str] = None,
        artifact_ids: List[str] = None,
        status: str = "OK"
    ) -> "TraceStep":
        """OUTPUT Step 생성"""
        return cls(
            step_id=f"{agent_id}.output",
            type=StepType.OUTPUT,
            status=status,
            timestamp=timestamp,
            payload_summary=OutputStepPayload(
                output_keys=output_keys,
                artifact_ids=artifact_ids
            ),
            agent_id=agent_id
        )


@dataclass
class AgentTrace:
    """Agent 실행 Trace (v1.0 스키마)"""
    agent_id: str
    preset: str = ""
    purpose: str = ""
    status: str = "PENDING"
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    steps: List[TraceStep] = field(default_factory=list)
    
    # 내부 집계용 (to_dict에서 선택적 출력)
    duration_ms: Optional[int] = None
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """스키마 v1.0 형식으로 변환"""
        result = {
            "agent_id": self.agent_id,
            "preset": self.preset,
            "purpose": self.purpose,
            "status": self.status,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "steps": [s.to_dict() for s in self.steps]  # 항상 배열 (빈 배열 가능)
        }
        # None 값 제거
        result = {k: v for k, v in result.items() if v is not None}
        # steps는 빈 배열이어도 유지
        if "steps" not in result:
            result["steps"] = []
        return result


@dataclass
class TraceArtifact:
    """
    생성된 Artifact 정보 (v1.0 스키마)
    
    {
      "artifact_id": "flood_depth_map",
      "type": "raster",
      "path": "outputs/maps/flood_depth.tif",
      "created_by": "executor_01",
      "created_at": "2026-01-01T12:05:40Z"
    }
    """
    artifact_id: str
    type: str
    path: str
    created_by: str  # agent_id
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        result = {
            "artifact_id": self.artifact_id,
            "type": self.type,
            "path": self.path,
            "created_by": self.created_by,
        }
        if self.created_at:
            result["created_at"] = self.created_at
        return result


@dataclass
class TraceError:
    """
    에러 정보 (v1.0 스키마)
    
    {
      "agent_id": "executor_01",
      "step_id": "executor_01.tool_python_exec",
      "type": "TOOL_ERROR",
      "message": "SWMM 실행 실패",
      "timestamp": "2026-01-01T12:03:10Z",
      "recoverable": false
    }
    """
    agent_id: str
    step_id: str
    type: str  # TOOL_ERROR, LLM_ERROR, VALIDATION_ERROR, etc.
    message: str
    timestamp: str
    recoverable: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "step_id": self.step_id,
            "type": self.type,
            "message": self.message,
            "timestamp": self.timestamp,
            "recoverable": self.recoverable
        }


@dataclass
class ExecutionConfig:
    """실행 설정"""
    mode: str = "sequential"
    retry_count: int = 0
    max_retries: int = 3
    stop_on_failure: bool = True
    
    def to_dict(self) -> Dict:
        return {
            "mode": self.mode,
            "retry_count": self.retry_count,
        }


@dataclass
class TraceSummary:
    """
    Trace 요약 정보 (v1.0 스키마)
    
    {
      "total_agents": 4,
      "completed_agents": 4,
      "failed_agents": 0,
      "total_llm_calls": 5,
      "total_tool_calls": 3,
      "total_tokens": 12450,
      "total_duration_ms": 392000
    }
    """
    total_agents: int = 0
    completed_agents: int = 0
    failed_agents: int = 0
    total_llm_calls: int = 0
    total_tool_calls: int = 0
    total_tokens: int = 0
    total_duration_ms: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "total_agents": self.total_agents,
            "completed_agents": self.completed_agents,
            "failed_agents": self.failed_agents,
            "total_llm_calls": self.total_llm_calls,
            "total_tool_calls": self.total_tool_calls,
            "total_tokens": self.total_tokens,
            "total_duration_ms": self.total_duration_ms,
        }


@dataclass 
class TraceDocument:
    """trace.json 전체 문서 (v1.0 스키마)"""
    run_id: str
    project_id: str
    
    # 메타데이터
    trace_version: str = "1.0"
    project_name: str = ""
    
    # 상태
    status: RunStatus = RunStatus.CREATED
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    duration_ms: Optional[int] = None
    
    # 실행 설정
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    
    # 에이전트
    agents: List[AgentTrace] = field(default_factory=list)
    
    # 아티팩트
    artifacts: List[TraceArtifact] = field(default_factory=list)
    
    # 에러
    errors: List[TraceError] = field(default_factory=list)
    
    # 요약
    summary: TraceSummary = field(default_factory=TraceSummary)
    
    def to_dict(self) -> Dict:
        """trace.json 스키마에 맞게 변환"""
        return {
            "trace_version": self.trace_version,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "status": self.status.value if isinstance(self.status, RunStatus) else self.status,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": self.duration_ms,
            "execution": self.execution.to_dict(),
            "agents": [a.to_dict() for a in self.agents],
            "artifacts": [a.to_dict() for a in self.artifacts],
            "errors": [e.to_dict() for e in self.errors],
            "summary": self.summary.to_dict(),
        }


@dataclass
class TraceEvent:
    """events.jsonl 단일 이벤트"""
    ts: str  # ISO timestamp
    type: EventType
    run_id: str
    
    # 선택적 필드
    agent_id: Optional[str] = None
    step_id: Optional[str] = None
    step_type: Optional[str] = None
    
    # 상세 데이터
    model: Optional[str] = None
    tokens: Optional[int] = None
    tool_name: Optional[str] = None
    message: Optional[str] = None
    level: Optional[str] = None
    error: Optional[str] = None
    data: Optional[Dict] = None
    
    def to_json_line(self) -> str:
        """JSONL 한 줄로 변환"""
        obj = {"ts": self.ts, "type": self.type.value, "run_id": self.run_id}
        
        if self.agent_id:
            obj["agent_id"] = self.agent_id
        if self.step_id:
            obj["step_id"] = self.step_id
        if self.step_type:
            obj["step_type"] = self.step_type
        if self.model:
            obj["model"] = self.model
        if self.tokens:
            obj["tokens"] = self.tokens
        if self.tool_name:
            obj["tool_name"] = self.tool_name
        if self.message:
            obj["message"] = self.message
        if self.level:
            obj["level"] = self.level
        if self.error:
            obj["error"] = self.error
        if self.data:
            obj["data"] = self.data
            
        return json.dumps(obj, ensure_ascii=False)


# ============================================================================
# Trace Store
# ============================================================================

class TraceStore:
    """
    Trace 저장소 관리
    
    사용법:
        store = TraceStore(base_dir)
        
        # Run 시작
        store.start_run(run_id, project_id, project_name, agents_config, execution_config)
        
        # 이벤트 기록
        store.log_event(run_id, EventType.AGENT_START, agent_id="planner")
        store.add_step(run_id, step)
        
        # Run 완료
        store.complete_run(run_id, status)
        
        # 조회
        trace = store.get_trace(run_id)
        events = store.get_events(run_id)
    """
    
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # 메모리 캐시 (활성 Run)
        self._active_traces: Dict[str, TraceDocument] = {}
        self._active_agents: Dict[str, Dict[str, AgentTrace]] = {}
    
    def _get_run_dir(self, project_id: str, run_id: str) -> Path:
        return self.base_dir / project_id / run_id
    
    def _get_trace_path(self, project_id: str, run_id: str) -> Path:
        return self._get_run_dir(project_id, run_id) / "trace.json"
    
    def _get_events_path(self, project_id: str, run_id: str) -> Path:
        return self._get_run_dir(project_id, run_id) / "events.jsonl"
    
    # ========== Run 관리 ==========
    
    def start_run(
        self, 
        run_id: str, 
        project_id: str, 
        project_name: str = "",
        agents_config: List[Dict] = None,
        execution_config: Dict = None,
        trace_level: str = "standard"
    ) -> TraceDocument:
        """Run 시작 - Trace 초기화"""
        
        # 디렉토리 생성
        run_dir = self._get_run_dir(project_id, run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # ExecutionConfig
        exec_config = ExecutionConfig()
        if execution_config:
            exec_config.mode = execution_config.get("mode", "sequential")
            exec_config.max_retries = execution_config.get("max_retries", 3)
            exec_config.stop_on_failure = execution_config.get("stop_on_failure", True)
        
        # TraceDocument 생성
        trace = TraceDocument(
            run_id=run_id,
            project_id=project_id,
            project_name=project_name,
            status=RunStatus.RUNNING,
            started_at=datetime.utcnow().isoformat() + "Z",
            execution=exec_config
        )
        
        # Agent Trace 초기화
        if agents_config:
            for agent_conf in agents_config:
                agent_trace = AgentTrace(
                    agent_id=agent_conf.get("id", "unknown"),
                    preset=agent_conf.get("preset", ""),
                    purpose=agent_conf.get("purpose", "")
                )
                trace.agents.append(agent_trace)
            trace.summary.total_agents = len(agents_config)
        
        # 메모리 캐시
        self._active_traces[run_id] = trace
        self._active_agents[run_id] = {a.agent_id: a for a in trace.agents}
        
        # trace.json 저장
        self._save_trace(trace)
        
        # 시작 이벤트 기록
        self.log_event(run_id, project_id, EventType.RUN_START)
        
        logger.info(f"[TraceStore] Run started: {run_id}")
        return trace
    
    def complete_run(
        self, 
        run_id: str, 
        project_id: str,
        status: RunStatus = RunStatus.COMPLETED,
        error: str = None
    ) -> Optional[TraceDocument]:
        """Run 완료 - Trace 마무리"""
        
        trace = self._active_traces.get(run_id)
        if not trace:
            trace = self.get_trace(project_id, run_id)
            if not trace:
                logger.warning(f"[TraceStore] Trace not found: {run_id}")
                return None
        
        trace.status = status
        trace.ended_at = datetime.utcnow().isoformat() + "Z"
        
        # duration 계산
        if trace.started_at:
            started = datetime.fromisoformat(trace.started_at.replace("Z", "+00:00"))
            ended = datetime.fromisoformat(trace.ended_at.replace("Z", "+00:00"))
            trace.duration_ms = int((ended - started).total_seconds() * 1000)
        
        # 에러 기록
        if error:
            trace.errors.append(TraceError(
                timestamp=trace.ended_at,
                error_type="RUN_ERROR",
                message=error
            ))
        
        # summary 집계
        self._aggregate_summary(trace)
        
        # 저장
        self._save_trace(trace)
        
        # 완료 이벤트
        event_type = {
            RunStatus.COMPLETED: EventType.RUN_COMPLETE,
            RunStatus.FAILED: EventType.RUN_FAILED,
            RunStatus.STOPPED: EventType.RUN_STOPPED,
        }.get(status, EventType.RUN_COMPLETE)
        
        self.log_event(run_id, project_id, event_type, error=error)
        
        # 캐시 정리
        self._active_traces.pop(run_id, None)
        self._active_agents.pop(run_id, None)
        
        logger.info(f"[TraceStore] Run completed: {run_id} ({status.value})")
        return trace
    
    # ========== Agent 관리 ==========
    
    def start_agent(self, run_id: str, project_id: str, agent_id: str):
        """Agent 실행 시작"""
        agent = self._get_active_agent(run_id, agent_id)
        if agent:
            agent.status = "RUNNING"
            agent.started_at = datetime.utcnow().isoformat() + "Z"
            self._save_active_trace(run_id)
        
        self.log_event(run_id, project_id, EventType.AGENT_START, agent_id=agent_id)
    
    def complete_agent(
        self, 
        run_id: str, 
        project_id: str,
        agent_id: str, 
        status: str = "COMPLETED",
        error: str = None
    ):
        """Agent 실행 완료"""
        agent = self._get_active_agent(run_id, agent_id)
        if agent:
            agent.status = status
            agent.ended_at = datetime.utcnow().isoformat() + "Z"
            
            if agent.started_at:
                started = datetime.fromisoformat(agent.started_at.replace("Z", "+00:00"))
                ended = datetime.fromisoformat(agent.ended_at.replace("Z", "+00:00"))
                agent.duration_ms = int((ended - started).total_seconds() * 1000)
            
            # tokens 집계 (v1.0 스키마: LLM step의 tokens.total)
            def get_step_tokens(step: TraceStep) -> int:
                # LLM step은 tokens 객체 사용
                if step.tokens and hasattr(step.tokens, 'total'):
                    return step.tokens.total
                # 구버전 호환
                if step.payload_summary and hasattr(step.payload_summary, 'tokens'):
                    return step.payload_summary.tokens or 0
                return 0
            
            agent.total_tokens = sum(get_step_tokens(s) for s in agent.steps)
            agent.total_cost_usd = agent.total_tokens * 0.00001
            
            if error:
                agent.error = error
            
            self._save_active_trace(run_id)
        
        event_type = EventType.AGENT_COMPLETE if status == "COMPLETED" else EventType.AGENT_FAILED
        self.log_event(run_id, project_id, event_type, agent_id=agent_id, error=error)
    
    # ========== Step 관리 ==========
    
    def add_step(self, run_id: str, project_id: str, step: TraceStep):
        """Step 추가"""
        agent = self._get_active_agent(run_id, step.agent_id)
        if agent:
            existing = next((s for s in agent.steps if s.step_id == step.step_id), None)
            if existing:
                # 기존 step 교체 (더 깔끔한 업데이트)
                idx = agent.steps.index(existing)
                agent.steps[idx] = step
            else:
                agent.steps.append(step)
            
            self._save_active_trace(run_id)
        
        # 이벤트 기록
        step_type_str = step.type.value if isinstance(step.type, StepType) else step.type
        
        if step.status == "RUNNING":
            self.log_event(
                run_id, project_id, EventType.STEP_START,
                agent_id=step.agent_id,
                step_id=step.step_id,
                step_type=step_type_str
            )
        elif step.status in ("OK", "COMPLETED"):
            # LLM step은 tokens와 model 정보 포함
            tokens_total = step.tokens.total if step.tokens else None
            tool_name = None
            if step.payload_summary and hasattr(step.payload_summary, 'tool_name'):
                tool_name = step.payload_summary.tool_name
            
            self.log_event(
                run_id, project_id, EventType.STEP_COMPLETE,
                agent_id=step.agent_id,
                step_id=step.step_id,
                tokens=tokens_total,
                model=step.model,
                tool_name=tool_name
            )
    
    # ========== Artifact 관리 ==========
    
    def add_artifact(
        self, 
        run_id: str, 
        project_id: str,
        artifact_id: str,
        artifact_type: str,
        path: str,
        created_by: str,
        created_at: str = None
    ):
        """Artifact 추가 (v1.0 스키마)"""
        trace = self._active_traces.get(run_id)
        if trace:
            artifact = TraceArtifact(
                artifact_id=artifact_id,
                type=artifact_type,
                path=path,
                created_by=created_by,
                created_at=created_at or (datetime.utcnow().isoformat() + "Z")
            )
            trace.artifacts.append(artifact)
            self._save_trace(trace)
    
    # ========== Error 관리 ==========
    
    def add_error(
        self,
        run_id: str,
        project_id: str,
        agent_id: str,
        step_id: str,
        error_type: str,
        message: str,
        timestamp: str = None,
        recoverable: bool = False
    ):
        """에러 추가 (v1.0 스키마)"""
        trace = self._active_traces.get(run_id)
        if trace:
            error = TraceError(
                agent_id=agent_id,
                step_id=step_id,
                type=error_type,
                message=message,
                timestamp=timestamp or (datetime.utcnow().isoformat() + "Z"),
                recoverable=recoverable
            )
            trace.errors.append(error)
            trace.execution.retry_count += 1
            self._save_trace(trace)
        
        self.log_event(
            run_id, project_id, EventType.ERROR,
            agent_id=agent_id,
            step_id=step_id,
            error=message
        )
    
    # ========== 이벤트 로깅 ==========
    
    def log_event(
        self,
        run_id: str,
        project_id: str,
        event_type: EventType,
        agent_id: str = None,
        step_id: str = None,
        step_type: str = None,
        model: str = None,
        tokens: int = None,
        tool_name: str = None,
        message: str = None,
        level: str = None,
        error: str = None,
        data: Dict = None
    ):
        """이벤트 기록 (events.jsonl)"""
        event = TraceEvent(
            ts=datetime.utcnow().isoformat() + "Z",
            type=event_type,
            run_id=run_id,
            agent_id=agent_id,
            step_id=step_id,
            step_type=step_type,
            model=model,
            tokens=tokens,
            tool_name=tool_name,
            message=message,
            level=level,
            error=error,
            data=data
        )
        
        events_path = self._get_events_path(project_id, run_id)
        events_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(events_path, 'a', encoding='utf-8') as f:
            f.write(event.to_json_line() + '\n')
    
    def log(
        self, 
        run_id: str, 
        project_id: str,
        level: str, 
        component: str, 
        message: str
    ):
        """일반 로그 기록"""
        self.log_event(
            run_id, project_id, EventType.LOG,
            agent_id=component,
            message=message,
            level=level
        )
    
    # ========== 조회 ==========
    
    def get_trace(self, project_id: str, run_id: str) -> Optional[TraceDocument]:
        """trace.json 조회"""
        if run_id in self._active_traces:
            return self._active_traces[run_id]
        
        trace_path = self._get_trace_path(project_id, run_id)
        if not trace_path.exists():
            return None
        
        try:
            with open(trace_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return self._dict_to_trace(data)
        except Exception as e:
            logger.error(f"[TraceStore] Failed to load trace: {e}")
            return None
    
    def get_events(
        self, 
        project_id: str, 
        run_id: str, 
        limit: int = None,
        event_types: List[EventType] = None
    ) -> List[Dict]:
        """events.jsonl 조회"""
        events_path = self._get_events_path(project_id, run_id)
        if not events_path.exists():
            return []
        
        events = []
        with open(events_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    
                    if event_types:
                        if event.get("type") not in [e.value for e in event_types]:
                            continue
                    
                    events.append(event)
                    
                    if limit and len(events) >= limit:
                        break
                except json.JSONDecodeError:
                    continue
        
        return events
    
    def list_runs(self, project_id: str) -> List[Dict]:
        """프로젝트의 Run 목록 조회"""
        project_dir = self.base_dir / project_id
        if not project_dir.exists():
            return []
        
        runs = []
        for run_dir in project_dir.iterdir():
            if not run_dir.is_dir():
                continue
            
            trace_path = run_dir / "trace.json"
            if trace_path.exists():
                try:
                    with open(trace_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    runs.append({
                        "run_id": data.get("run_id"),
                        "status": data.get("status"),
                        "started_at": data.get("started_at"),
                        "ended_at": data.get("ended_at"),
                        "duration_ms": data.get("duration_ms"),
                    })
                except:
                    continue
        
        runs.sort(key=lambda x: x.get("started_at", ""), reverse=True)
        return runs
    
    # ========== 내부 메서드 ==========
    
    def _get_active_agent(self, run_id: str, agent_id: str) -> Optional[AgentTrace]:
        agents = self._active_agents.get(run_id, {})
        return agents.get(agent_id)
    
    def _save_trace(self, trace: TraceDocument):
        trace_path = self._get_trace_path(trace.project_id, trace.run_id)
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(trace_path, 'w', encoding='utf-8') as f:
            json.dump(trace.to_dict(), f, ensure_ascii=False, indent=2)
    
    def _save_active_trace(self, run_id: str):
        trace = self._active_traces.get(run_id)
        if trace:
            self._save_trace(trace)
    
    def _aggregate_summary(self, trace: TraceDocument):
        """Summary 집계 (v1.0 스키마)"""
        trace.summary.total_agents = len(trace.agents)
        trace.summary.completed_agents = sum(1 for a in trace.agents if a.status == "COMPLETED")
        trace.summary.failed_agents = sum(1 for a in trace.agents if a.status == "FAILED")
        
        # LLM/TOOL 호출 수 집계
        total_llm_calls = 0
        total_tool_calls = 0
        total_tokens = 0
        
        for agent in trace.agents:
            for step in agent.steps:
                step_type = step.type.value if isinstance(step.type, StepType) else step.type
                if step_type == "LLM":
                    total_llm_calls += 1
                    if step.tokens:
                        total_tokens += step.tokens.total
                elif step_type == "TOOL":
                    total_tool_calls += 1
        
        trace.summary.total_llm_calls = total_llm_calls
        trace.summary.total_tool_calls = total_tool_calls
        trace.summary.total_tokens = total_tokens
        trace.summary.total_duration_ms = trace.duration_ms or 0
    
    def _dict_to_trace(self, data: Dict) -> TraceDocument:
        """Dict를 TraceDocument로 변환"""
        # ExecutionConfig
        exec_data = data.get("execution", {})
        exec_config = ExecutionConfig(
            mode=exec_data.get("mode", "sequential"),
            retry_count=exec_data.get("retry_count", 0)
        )
        
        trace = TraceDocument(
            run_id=data.get("run_id", ""),
            project_id=data.get("project_id", ""),
            trace_version=data.get("trace_version", "1.0"),
            project_name=data.get("project_name", ""),
            status=RunStatus(data.get("status", "CREATED")),
            started_at=data.get("started_at"),
            ended_at=data.get("ended_at"),
            duration_ms=data.get("duration_ms"),
            execution=exec_config
        )
        
        # Summary (v1.0 스키마)
        summary_data = data.get("summary", {})
        trace.summary = TraceSummary(
            total_agents=summary_data.get("total_agents", 0),
            completed_agents=summary_data.get("completed_agents", 0),
            failed_agents=summary_data.get("failed_agents", 0),
            total_llm_calls=summary_data.get("total_llm_calls", 0),
            total_tool_calls=summary_data.get("total_tool_calls", 0),
            total_tokens=summary_data.get("total_tokens", 0),
            total_duration_ms=summary_data.get("total_duration_ms", 0)
        )
        
        # Agents
        for agent_data in data.get("agents", []):
            steps = []
            for step_data in agent_data.get("steps", []):
                # v1.0 스키마: type (새) vs step_type (구)
                step_type_str = step_data.get("type") or step_data.get("step_type")
                if isinstance(step_type_str, str):
                    step_type = StepType(step_type_str)
                else:
                    step_type = step_type_str
                
                # payload_summary 파싱
                payload_data = step_data.get("payload_summary", {})
                payload = PayloadSummary(
                    context=payload_data.get("context"),
                    previous_results=payload_data.get("previous_results"),
                    model=payload_data.get("model"),
                    tokens=payload_data.get("tokens"),
                    prompt_summary=payload_data.get("prompt_summary"),
                    response_summary=payload_data.get("response_summary"),
                    tool_name=payload_data.get("tool_name"),
                    tool_args=payload_data.get("tool_args"),
                    tool_result=payload_data.get("tool_result"),
                    output_keys=payload_data.get("output_keys"),
                    artifact_ids=payload_data.get("artifact_ids"),
                    error=payload_data.get("error")
                ) if payload_data else None
                
                steps.append(TraceStep(
                    step_id=step_data.get("step_id", ""),
                    type=step_type,
                    status=step_data.get("status", "OK"),
                    timestamp=step_data.get("timestamp"),
                    payload_summary=payload,
                    agent_id=step_data.get("agent_id")
                ))
            
            agent = AgentTrace(
                agent_id=agent_data.get("agent_id", ""),
                preset=agent_data.get("preset", ""),
                purpose=agent_data.get("purpose", ""),
                status=agent_data.get("status", "PENDING"),
                started_at=agent_data.get("started_at"),
                ended_at=agent_data.get("ended_at"),
                duration_ms=agent_data.get("duration_ms"),
                total_tokens=agent_data.get("total_tokens", 0),
                total_cost_usd=agent_data.get("total_cost_usd", 0.0),
                error=agent_data.get("error"),
                steps=steps
            )
            trace.agents.append(agent)
        
        # Artifacts (v1.0 스키마)
        for artifact_data in data.get("artifacts", []):
            trace.artifacts.append(TraceArtifact(
                artifact_id=artifact_data.get("artifact_id", ""),
                type=artifact_data.get("type", ""),
                path=artifact_data.get("path", ""),
                created_by=artifact_data.get("created_by", artifact_data.get("source_agent", "")),
                created_at=artifact_data.get("created_at")
            ))
        
        # Errors (v1.0 스키마)
        for error_data in data.get("errors", []):
            trace.errors.append(TraceError(
                agent_id=error_data.get("agent_id", ""),
                step_id=error_data.get("step_id", ""),
                type=error_data.get("type", error_data.get("error_type", "UNKNOWN")),
                message=error_data.get("message", ""),
                timestamp=error_data.get("timestamp", ""),
                recoverable=error_data.get("recoverable", False)
            ))
        
        return trace


# ============================================================================
# 싱글톤 인스턴스
# ============================================================================

_trace_store: Optional[TraceStore] = None

def get_trace_store(base_dir: Path = None) -> TraceStore:
    """TraceStore 싱글톤 반환"""
    global _trace_store
    if _trace_store is None:
        if base_dir is None:
            base_dir = Path(__file__).parent.parent.parent / "traces"
        _trace_store = TraceStore(base_dir)
    return _trace_store
