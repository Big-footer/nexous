"""
NEXOUS Core - Trace Writer

TraceWriter는 NEXOUS 실행 엔진의 "블랙박스 기록기"다.
실행 흐름을 바꾸지 않고, 옆에서 전부 기록만 한다.

❌ 판단 ❌ 실행 ❌ 제어
⭕ 기록 ⭕ 상태 전이 ⭕ 증거 생성

⚠️ 이 인터페이스는 API 계약입니다. 절대 변경하지 마세요.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

from .state import RunStatus, AgentStatus, StepType, StepStatus

logger = logging.getLogger(__name__)


# ============================================================================
# Utility
# ============================================================================

def utc_now() -> str:
    """현재 UTC 시간을 ISO 8601 형식으로 반환"""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def calc_duration_ms(started_at: str, ended_at: str) -> int:
    """두 ISO 시간 사이의 밀리초 계산"""
    started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    ended = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
    return int((ended - started).total_seconds() * 1000)


# ============================================================================
# Data Models (trace.json v1.0 스키마)
# ============================================================================

@dataclass
class TokenUsage:
    """LLM 토큰 사용량"""
    input: int = 0
    output: int = 0
    total: int = 0
    
    def to_dict(self) -> Dict:
        return {"input": self.input, "output": self.output, "total": self.total}


@dataclass
class Step:
    """실행 Step (v1.0 스키마)"""
    step_id: str
    type: StepType
    status: StepStatus = StepStatus.OK
    
    # INPUT/OUTPUT용
    timestamp: Optional[str] = None
    payload_summary: Optional[Dict] = None
    
    # LLM/TOOL 공통
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    latency_ms: Optional[int] = None
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    
    # LLM 전용
    provider: Optional[str] = None
    model: Optional[str] = None
    tokens: Optional[TokenUsage] = None
    
    # TOOL 전용
    tool_name: Optional[str] = None
    
    # 에러
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        result = {
            "step_id": self.step_id,
            "type": self.type.value if isinstance(self.type, StepType) else self.type,
            "status": self.status.value if isinstance(self.status, StepStatus) else self.status,
        }
        
        step_type = self.type.value if isinstance(self.type, StepType) else self.type
        
        if step_type == "LLM":
            if self.provider: result["provider"] = self.provider
            if self.model: result["model"] = self.model
            if self.started_at: result["started_at"] = self.started_at
            if self.ended_at: result["ended_at"] = self.ended_at
            if self.latency_ms is not None: result["latency_ms"] = self.latency_ms
            if self.tokens: result["tokens"] = self.tokens.to_dict()
            if self.input_summary: result["input_summary"] = self.input_summary
            if self.output_summary: result["output_summary"] = self.output_summary
            
        elif step_type == "TOOL":
            if self.tool_name: result["tool_name"] = self.tool_name
            if self.started_at: result["started_at"] = self.started_at
            if self.ended_at: result["ended_at"] = self.ended_at
            if self.latency_ms is not None: result["latency_ms"] = self.latency_ms
            if self.input_summary: result["input_summary"] = self.input_summary
            if self.output_summary: result["output_summary"] = self.output_summary
            
        else:  # INPUT, OUTPUT
            if self.timestamp: result["timestamp"] = self.timestamp
            if self.payload_summary: result["payload_summary"] = self.payload_summary
        
        if self.error: result["error"] = self.error
        return result


@dataclass
class Agent:
    """Agent 실행 기록"""
    agent_id: str
    preset: str = ""
    purpose: str = ""
    status: AgentStatus = AgentStatus.IDLE
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    steps: List[Step] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        result = {
            "agent_id": self.agent_id,
            "preset": self.preset,
            "purpose": self.purpose,
            "status": self.status.value if isinstance(self.status, AgentStatus) else self.status,
            "steps": [s.to_dict() for s in self.steps]
        }
        if self.started_at: result["started_at"] = self.started_at
        if self.ended_at: result["ended_at"] = self.ended_at
        return result


@dataclass
class Artifact:
    """생성된 Artifact"""
    artifact_id: str
    type: str
    path: str
    created_by: str
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        result = {
            "artifact_id": self.artifact_id,
            "type": self.type,
            "path": self.path,
            "created_by": self.created_by,
        }
        if self.created_at: result["created_at"] = self.created_at
        return result


@dataclass
class Error:
    """에러 정보"""
    agent_id: str
    step_id: str
    type: str
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
class Summary:
    """실행 요약"""
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
            "total_duration_ms": self.total_duration_ms
        }


@dataclass
class Trace:
    """trace.json 전체 문서"""
    run_id: str
    project_id: str
    trace_version: str = "1.0"
    status: RunStatus = RunStatus.CREATED
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    duration_ms: Optional[int] = None
    execution_mode: str = "sequential"
    retry_count: int = 0
    agents: List[Agent] = field(default_factory=list)
    artifacts: List[Artifact] = field(default_factory=list)
    errors: List[Error] = field(default_factory=list)
    summary: Summary = field(default_factory=Summary)
    
    def to_dict(self) -> Dict:
        return {
            "trace_version": self.trace_version,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "status": self.status.value if isinstance(self.status, RunStatus) else self.status,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": self.duration_ms,
            "execution": {
                "mode": self.execution_mode,
                "retry_count": self.retry_count
            },
            "agents": [a.to_dict() for a in self.agents],
            "artifacts": [a.to_dict() for a in self.artifacts],
            "errors": [e.to_dict() for e in self.errors],
            "summary": self.summary.to_dict()
        }


# ============================================================================
# Trace Writer (API 계약 - 인터페이스 변경 금지)
# ============================================================================

class TraceWriter:
    """
    NEXOUS 실행 기록기 (블랙박스)
    
    ⚠️ 이 인터페이스는 API 계약입니다. 절대 변경하지 마세요.
    
    사용법:
        writer = TraceWriter(base_dir="traces")
        
        # Run
        writer.start_run("flood_analysis", "run_001", "sequential")
        
        # Agent
        writer.start_agent("executor_01", "executor", "SWMM 시뮬레이션")
        
        # Steps
        writer.log_step("executor_01", "INPUT", "OK", payload={...})
        writer.log_step("executor_01", "LLM", "OK", payload={...}, metadata={...})
        writer.log_step("executor_01", "TOOL", "OK", payload={...}, metadata={...})
        writer.log_step("executor_01", "OUTPUT", "OK", payload={...})
        
        # End
        writer.end_agent("executor_01", "COMPLETED")
        writer.end_run("COMPLETED")
    """
    
    def __init__(self, base_dir: str = "traces"):
        self.base_dir = Path(base_dir)
        self._trace: Optional[Trace] = None
        self._agents_map: Dict[str, Agent] = {}
        self._step_counters: Dict[str, Dict[str, int]] = {}  # agent_id -> {step_type -> count}
    
    # ========================================================================
    # API 계약 - Run 관리
    # ========================================================================
    
    def start_run(self, project_id: str, run_id: str, execution_mode: str) -> None:
        """Run 시작 기록"""
        self._trace = Trace(
            run_id=run_id,
            project_id=project_id,
            status=RunStatus.RUNNING,
            started_at=utc_now(),
            execution_mode=execution_mode
        )
        self._agents_map.clear()
        self._step_counters.clear()
        self._save()
        logger.info(f"[TraceWriter] Run started: {project_id}/{run_id}")
    
    def end_run(self, status: str) -> None:
        """Run 종료 기록 (COMPLETED / FAILED)"""
        if not self._trace:
            return
        
        self._trace.status = RunStatus(status)
        self._trace.ended_at = utc_now()
        
        if self._trace.started_at:
            self._trace.duration_ms = calc_duration_ms(self._trace.started_at, self._trace.ended_at)
        
        self._aggregate_summary()
        self._save()
        logger.info(f"[TraceWriter] Run ended: {self._trace.run_id} ({status})")
    
    # ========================================================================
    # API 계약 - Agent 관리
    # ========================================================================
    
    def start_agent(self, agent_id: str, preset: str, purpose: str) -> None:
        """Agent 실행 시작"""
        if not self._trace:
            return
        
        agent = Agent(
            agent_id=agent_id,
            preset=preset,
            purpose=purpose,
            status=AgentStatus.RUNNING,
            started_at=utc_now()
        )
        self._trace.agents.append(agent)
        self._agents_map[agent_id] = agent
        self._step_counters[agent_id] = {"LLM": 0, "TOOL": 0}
        self._save()
        logger.debug(f"[TraceWriter] Agent started: {agent_id}")
    
    def end_agent(self, agent_id: str, status: str) -> None:
        """Agent 실행 종료"""
        agent = self._agents_map.get(agent_id)
        if not agent:
            return
        
        agent.status = AgentStatus(status)
        agent.ended_at = utc_now()
        self._save()
        logger.debug(f"[TraceWriter] Agent ended: {agent_id} ({status})")
    
    # ========================================================================
    # API 계약 - Step 기록
    # ========================================================================
    
    def log_step(
        self,
        agent_id: str,
        step_type: str,
        status: str,
        payload: dict | None = None,
        metadata: dict | None = None
    ) -> None:
        """
        Step 단위 기록
        
        Args:
            agent_id: Agent ID
            step_type: INPUT / LLM / TOOL / OUTPUT
            status: OK / ERROR
            payload: Step별 데이터
                - INPUT: {"context": [...], "previous_results": [...]}
                - LLM: {"input_summary": "...", "output_summary": "..."}
                - TOOL: {"tool_name": "...", "input_summary": "...", "output_summary": "..."}
                - OUTPUT: {"output_keys": [...], "artifact_ids": [...]}
            metadata: 추가 메타데이터
                - LLM: {"provider": "openai", "model": "gpt-4o", "tokens_input": 1000, "tokens_output": 500, "latency_ms": 2000}
                - TOOL: {"latency_ms": 5000}
        """
        agent = self._agents_map.get(agent_id)
        if not agent:
            return
        
        payload = payload or {}
        metadata = metadata or {}
        
        # Step ID 생성
        step_id = self._generate_step_id(agent_id, step_type, payload)
        
        # Step 생성
        step = Step(
            step_id=step_id,
            type=StepType(step_type),
            status=StepStatus(status)
        )
        
        now = utc_now()
        
        if step_type == "INPUT":
            step.timestamp = now
            step.payload_summary = {
                "context": payload.get("context", []),
                "previous_results": payload.get("previous_results", [])
            }
            
        elif step_type == "LLM":
            step.provider = metadata.get("provider", "unknown")
            step.model = metadata.get("model", "unknown")
            step.started_at = metadata.get("started_at", now)
            step.ended_at = metadata.get("ended_at", now)
            step.latency_ms = metadata.get("latency_ms")
            
            tokens_in = metadata.get("tokens_input", 0)
            tokens_out = metadata.get("tokens_output", 0)
            step.tokens = TokenUsage(input=tokens_in, output=tokens_out, total=tokens_in + tokens_out)
            
            step.input_summary = payload.get("input_summary")
            step.output_summary = payload.get("output_summary")
            
        elif step_type == "TOOL":
            step.tool_name = payload.get("tool_name", "unknown")
            step.started_at = metadata.get("started_at", now)
            step.ended_at = metadata.get("ended_at", now)
            step.latency_ms = metadata.get("latency_ms")
            step.input_summary = payload.get("input_summary")
            step.output_summary = payload.get("output_summary")
            
        elif step_type == "OUTPUT":
            step.timestamp = now
            step.payload_summary = {
                "output_keys": payload.get("output_keys", []),
                "artifact_ids": payload.get("artifact_ids", [])
            }
        
        if status == "ERROR":
            step.error = payload.get("error", metadata.get("error"))
        
        agent.steps.append(step)
        self._save()
    
    # ========================================================================
    # API 계약 - Error 기록
    # ========================================================================
    
    def log_error(
        self,
        agent_id: str,
        step_id: str,
        error_type: str,
        message: str,
        recoverable: bool
    ) -> None:
        """Error 기록"""
        if not self._trace:
            return
        
        error = Error(
            agent_id=agent_id,
            step_id=step_id,
            type=error_type,
            message=message,
            timestamp=utc_now(),
            recoverable=recoverable
        )
        self._trace.errors.append(error)
        self._trace.retry_count += 1
        self._save()
    
    # ========================================================================
    # API 계약 - Artifact 기록
    # ========================================================================
    
    def register_artifact(
        self,
        artifact_id: str,
        artifact_type: str,
        path: str,
        created_by: str
    ) -> None:
        """Artifact 기록"""
        if not self._trace:
            return
        
        artifact = Artifact(
            artifact_id=artifact_id,
            type=artifact_type,
            path=path,
            created_by=created_by,
            created_at=utc_now()
        )
        self._trace.artifacts.append(artifact)
        self._save()
    
    # ========================================================================
    # 조회 메서드
    # ========================================================================
    
    def get_trace(self) -> Optional[Dict]:
        """현재 Trace 반환"""
        return self._trace.to_dict() if self._trace else None
    
    def get_trace_path(self) -> Optional[Path]:
        """Trace 파일 경로 반환"""
        if not self._trace:
            return None
        return self.base_dir / self._trace.project_id / self._trace.run_id / "trace.json"
    
    # ========================================================================
    # 내부 메서드
    # ========================================================================
    
    def _generate_step_id(self, agent_id: str, step_type: str, payload: dict) -> str:
        """Step ID 생성"""
        if step_type == "INPUT":
            return f"{agent_id}.input"
        elif step_type == "OUTPUT":
            return f"{agent_id}.output"
        elif step_type == "LLM":
            counter = self._step_counters.get(agent_id, {})
            count = counter.get("LLM", 0) + 1
            counter["LLM"] = count
            self._step_counters[agent_id] = counter
            return f"{agent_id}.llm_{count:02d}"
        elif step_type == "TOOL":
            tool_name = payload.get("tool_name", "unknown")
            return f"{agent_id}.tool_{tool_name}"
        return f"{agent_id}.{step_type.lower()}"
    
    def _aggregate_summary(self) -> None:
        """Summary 자동 집계"""
        if not self._trace:
            return
        
        summary = self._trace.summary
        summary.total_agents = len(self._trace.agents)
        summary.completed_agents = sum(1 for a in self._trace.agents if a.status == AgentStatus.COMPLETED)
        summary.failed_agents = sum(1 for a in self._trace.agents if a.status == AgentStatus.FAILED)
        
        total_llm = 0
        total_tool = 0
        total_tokens = 0
        
        for agent in self._trace.agents:
            for step in agent.steps:
                step_type = step.type.value if isinstance(step.type, StepType) else step.type
                if step_type == "LLM":
                    total_llm += 1
                    if step.tokens:
                        total_tokens += step.tokens.total
                elif step_type == "TOOL":
                    total_tool += 1
        
        summary.total_llm_calls = total_llm
        summary.total_tool_calls = total_tool
        summary.total_tokens = total_tokens
        summary.total_duration_ms = self._trace.duration_ms or 0
    
    def _save(self) -> None:
        """trace.json 저장"""
        if not self._trace:
            return
        
        trace_dir = self.base_dir / self._trace.project_id / self._trace.run_id
        trace_dir.mkdir(parents=True, exist_ok=True)
        
        trace_path = trace_dir / "trace.json"
        with open(trace_path, 'w', encoding='utf-8') as f:
            json.dump(self._trace.to_dict(), f, ensure_ascii=False, indent=2)
