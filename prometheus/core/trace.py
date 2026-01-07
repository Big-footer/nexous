"""
NEXUS Trace System

프로젝트 실행 기록을 저장하고 추적합니다.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class TraceStatus(str, Enum):
    """Trace 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentCall(BaseModel):
    """Agent 호출 기록"""
    agent_name: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: TraceStatus = TraceStatus.PENDING
    
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    duration_ms: Optional[int] = None


class LLMCall(BaseModel):
    """LLM 호출 기록"""
    provider: str
    model: str
    called_at: datetime
    
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    latency_ms: int = 0
    cost_usd: float = 0.0
    
    success: bool = True
    error: Optional[str] = None


class ToolCall(BaseModel):
    """Tool 호출 기록"""
    tool_name: str
    called_at: datetime
    
    arguments: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Any] = None
    
    success: bool = True
    error: Optional[str] = None
    duration_ms: int = 0


class Trace(BaseModel):
    """
    실행 Trace
    
    한 번의 프로젝트 실행에 대한 전체 기록
    """
    # 식별자
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    
    # 시간 정보
    started_at: datetime = Field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None
    
    # 상태
    status: TraceStatus = TraceStatus.PENDING
    
    # 설정 스냅샷
    config_snapshot: Dict[str, Any] = Field(default_factory=dict)
    
    # 입력
    request: Optional[str] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)
    
    # 실행 기록
    agent_calls: List[AgentCall] = Field(default_factory=list)
    llm_calls: List[LLMCall] = Field(default_factory=list)
    tool_calls: List[ToolCall] = Field(default_factory=list)
    
    # 결과
    outputs: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[str] = Field(default_factory=list)  # artifact IDs
    
    # 에러
    error: Optional[str] = None
    error_traceback: Optional[str] = None
    
    # 통계
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    duration_ms: int = 0
    
    def start_agent(self, agent_name: str, input_data: Optional[Dict] = None) -> AgentCall:
        """Agent 실행 시작 기록"""
        call = AgentCall(
            agent_name=agent_name,
            started_at=datetime.now(),
            status=TraceStatus.RUNNING,
            input_data=input_data,
        )
        self.agent_calls.append(call)
        return call
    
    def finish_agent(
        self,
        agent_name: str,
        output_data: Optional[Dict] = None,
        error: Optional[str] = None,
    ):
        """Agent 실행 완료 기록"""
        for call in reversed(self.agent_calls):
            if call.agent_name == agent_name and call.status == TraceStatus.RUNNING:
                call.finished_at = datetime.now()
                call.output_data = output_data
                call.error = error
                call.status = TraceStatus.COMPLETED if not error else TraceStatus.FAILED
                call.duration_ms = int((call.finished_at - call.started_at).total_seconds() * 1000)
                break
    
    def log_llm_call(
        self,
        provider: str,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: int = 0,
        cost_usd: float = 0.0,
        success: bool = True,
        error: Optional[str] = None,
    ):
        """LLM 호출 기록"""
        call = LLMCall(
            provider=provider,
            model=model,
            called_at=datetime.now(),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            success=success,
            error=error,
        )
        self.llm_calls.append(call)
        
        # 통계 업데이트
        self.total_tokens += call.total_tokens
        self.total_cost_usd += cost_usd
    
    def log_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Any = None,
        success: bool = True,
        error: Optional[str] = None,
        duration_ms: int = 0,
    ):
        """Tool 호출 기록"""
        call = ToolCall(
            tool_name=tool_name,
            called_at=datetime.now(),
            arguments=arguments,
            result=result,
            success=success,
            error=error,
            duration_ms=duration_ms,
        )
        self.tool_calls.append(call)
    
    def complete(self, outputs: Optional[Dict] = None, artifacts: Optional[List[str]] = None):
        """Trace 완료"""
        self.finished_at = datetime.now()
        self.status = TraceStatus.COMPLETED
        self.outputs = outputs or {}
        self.artifacts = artifacts or []
        self.duration_ms = int((self.finished_at - self.started_at).total_seconds() * 1000)
    
    def fail(self, error: str, traceback: Optional[str] = None):
        """Trace 실패"""
        self.finished_at = datetime.now()
        self.status = TraceStatus.FAILED
        self.error = error
        self.error_traceback = traceback
        self.duration_ms = int((self.finished_at - self.started_at).total_seconds() * 1000)
    
    def get_summary(self) -> Dict[str, Any]:
        """Trace 요약"""
        return {
            "trace_id": self.trace_id,
            "project_name": self.project_name,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "agents_used": [c.agent_name for c in self.agent_calls],
            "llm_calls_count": len(self.llm_calls),
            "tool_calls_count": len(self.tool_calls),
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "artifacts_count": len(self.artifacts),
            "error": self.error,
        }


class TraceStore:
    """
    Trace 저장소
    
    Trace를 파일 시스템에 저장하고 조회합니다.
    """
    
    def __init__(self, base_dir: Union[str, Path] = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / ".nexus" / "traces"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self._index_file = self.base_dir / "index.json"
        self._index: Dict[str, Dict] = self._load_index()
    
    def _load_index(self) -> Dict[str, Dict]:
        """인덱스 로드"""
        if self._index_file.exists():
            try:
                with open(self._index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_index(self):
        """인덱스 저장"""
        with open(self._index_file, 'w', encoding='utf-8') as f:
            json.dump(self._index, f, ensure_ascii=False, indent=2, default=str)
    
    def save(self, trace: Trace) -> str:
        """Trace 저장"""
        # 프로젝트별 디렉토리
        if trace.project_id:
            trace_dir = self.base_dir / trace.project_id
        else:
            trace_dir = self.base_dir / "default"
        trace_dir.mkdir(parents=True, exist_ok=True)
        
        # JSON 파일로 저장
        trace_file = trace_dir / f"{trace.trace_id}.json"
        with open(trace_file, 'w', encoding='utf-8') as f:
            json.dump(trace.model_dump(mode='json'), f, ensure_ascii=False, indent=2, default=str)
        
        # 인덱스 업데이트
        self._index[trace.trace_id] = {
            "path": str(trace_file),
            "project_id": trace.project_id,
            "project_name": trace.project_name,
            "status": trace.status.value,
            "started_at": trace.started_at.isoformat(),
            "finished_at": trace.finished_at.isoformat() if trace.finished_at else None,
        }
        self._save_index()
        
        logger.info(f"Trace 저장: {trace.trace_id}")
        return trace.trace_id
    
    def load(self, trace_id: str) -> Optional[Trace]:
        """Trace 로드"""
        if trace_id not in self._index:
            return None
        
        trace_path = Path(self._index[trace_id]["path"])
        if not trace_path.exists():
            return None
        
        with open(trace_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return Trace(**data)
    
    def delete(self, trace_id: str) -> bool:
        """Trace 삭제"""
        if trace_id not in self._index:
            return False
        
        trace_path = Path(self._index[trace_id]["path"])
        if trace_path.exists():
            trace_path.unlink()
        
        del self._index[trace_id]
        self._save_index()
        return True
    
    def list_by_project(self, project_id: str) -> List[Dict]:
        """프로젝트별 Trace 목록"""
        return [
            {**v, "trace_id": k}
            for k, v in self._index.items()
            if v.get("project_id") == project_id
        ]
    
    def list_recent(self, limit: int = 20) -> List[Dict]:
        """최근 Trace 목록"""
        traces = [
            {**v, "trace_id": k}
            for k, v in self._index.items()
        ]
        traces.sort(key=lambda x: x.get("started_at", ""), reverse=True)
        return traces[:limit]
    
    def list_all(self) -> List[Dict]:
        """모든 Trace 목록"""
        return [
            {**v, "trace_id": k}
            for k, v in self._index.items()
        ]


# =============================================================================
# 싱글톤 인스턴스
# =============================================================================

_trace_store: Optional[TraceStore] = None

def get_trace_store() -> TraceStore:
    """TraceStore 싱글톤 반환"""
    global _trace_store
    if _trace_store is None:
        _trace_store = TraceStore()
    return _trace_store


def create_trace(
    project_id: Optional[str] = None,
    project_name: Optional[str] = None,
    request: Optional[str] = None,
    config: Optional[Dict] = None,
) -> Trace:
    """새 Trace 생성"""
    return Trace(
        project_id=project_id,
        project_name=project_name,
        request=request,
        config_snapshot=config or {},
        status=TraceStatus.RUNNING,
    )
