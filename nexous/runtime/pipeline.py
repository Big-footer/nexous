"""
NEXOUS Runtime - Pipeline

실행 파이프라인을 정의합니다.

플랫폼 책임:
- 파이프라인 정의 및 구성
- 단계별 실행 흐름 관리
- 조건부 분기 처리

주의: Pipeline은 "흐름"만 정의합니다.
각 단계에서 "무엇을 하는가"는 Agent의 책임입니다.
"""

from typing import Any, Callable, Dict, List, Optional, Union
from enum import Enum
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


class StepType(str, Enum):
    """파이프라인 단계 유형"""
    AGENT = "agent"         # Agent 실행
    CONDITION = "condition" # 조건부 분기
    PARALLEL = "parallel"   # 병렬 실행
    LOOP = "loop"           # 반복
    END = "end"             # 종료


@dataclass
class PipelineStep:
    """파이프라인 단계 정의"""
    name: str
    step_type: StepType
    agent_name: Optional[str] = None
    
    # 조건부 분기
    condition: Optional[Callable[[Dict], bool]] = None
    on_true: Optional[str] = None   # 조건 참일 때 다음 단계
    on_false: Optional[str] = None  # 조건 거짓일 때 다음 단계
    
    # 병렬 실행
    parallel_agents: List[str] = field(default_factory=list)
    
    # 다음 단계
    next_step: Optional[str] = None
    
    # 설정
    config: Dict[str, Any] = field(default_factory=dict)


class Pipeline:
    """
    Pipeline (NEXOUS 플랫폼 핵심)
    
    실행 파이프라인을 정의하고 구성합니다.
    파이프라인은 "어떤 순서로, 어떤 조건에서" 실행할지 정의합니다.
    """
    
    def __init__(self, name: str):
        self.name = name
        self._steps: Dict[str, PipelineStep] = {}
        self._start_step: Optional[str] = None
        
    def add_step(self, step: PipelineStep) -> "Pipeline":
        """단계 추가"""
        self._steps[step.name] = step
        if self._start_step is None:
            self._start_step = step.name
        return self
    
    def agent(
        self,
        name: str,
        agent_name: str,
        next_step: Optional[str] = None,
        config: Optional[Dict] = None,
    ) -> "Pipeline":
        """Agent 실행 단계 추가"""
        step = PipelineStep(
            name=name,
            step_type=StepType.AGENT,
            agent_name=agent_name,
            next_step=next_step,
            config=config or {},
        )
        return self.add_step(step)
    
    def condition(
        self,
        name: str,
        condition: Callable[[Dict], bool],
        on_true: str,
        on_false: str,
    ) -> "Pipeline":
        """조건부 분기 단계 추가"""
        step = PipelineStep(
            name=name,
            step_type=StepType.CONDITION,
            condition=condition,
            on_true=on_true,
            on_false=on_false,
        )
        return self.add_step(step)
    
    def parallel(
        self,
        name: str,
        agent_names: List[str],
        next_step: Optional[str] = None,
    ) -> "Pipeline":
        """병렬 실행 단계 추가"""
        step = PipelineStep(
            name=name,
            step_type=StepType.PARALLEL,
            parallel_agents=agent_names,
            next_step=next_step,
        )
        return self.add_step(step)
    
    def end(self, name: str = "end") -> "Pipeline":
        """종료 단계 추가"""
        step = PipelineStep(
            name=name,
            step_type=StepType.END,
        )
        return self.add_step(step)
    
    def set_start(self, step_name: str) -> "Pipeline":
        """시작 단계 설정"""
        if step_name not in self._steps:
            raise ValueError(f"Step not found: {step_name}")
        self._start_step = step_name
        return self
    
    def get_step(self, name: str) -> Optional[PipelineStep]:
        """단계 조회"""
        return self._steps.get(name)
    
    def get_start_step(self) -> Optional[PipelineStep]:
        """시작 단계 조회"""
        return self._steps.get(self._start_step) if self._start_step else None
    
    def get_next_step(self, current: str, context: Dict) -> Optional[PipelineStep]:
        """다음 단계 결정"""
        step = self._steps.get(current)
        if step is None:
            return None
        
        if step.step_type == StepType.END:
            return None
        
        if step.step_type == StepType.CONDITION:
            # 조건 평가
            if step.condition and step.condition(context):
                next_name = step.on_true
            else:
                next_name = step.on_false
        else:
            next_name = step.next_step
        
        return self._steps.get(next_name) if next_name else None
    
    def validate(self) -> List[str]:
        """파이프라인 유효성 검사"""
        errors = []
        
        if not self._start_step:
            errors.append("No start step defined")
        
        if self._start_step and self._start_step not in self._steps:
            errors.append(f"Start step not found: {self._start_step}")
        
        # 연결성 검사
        for name, step in self._steps.items():
            if step.next_step and step.next_step not in self._steps:
                errors.append(f"Step '{name}' references unknown next step: {step.next_step}")
            if step.on_true and step.on_true not in self._steps:
                errors.append(f"Step '{name}' references unknown on_true step: {step.on_true}")
            if step.on_false and step.on_false not in self._steps:
                errors.append(f"Step '{name}' references unknown on_false step: {step.on_false}")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "name": self.name,
            "start_step": self._start_step,
            "steps": {
                name: {
                    "type": step.step_type.value,
                    "agent_name": step.agent_name,
                    "next_step": step.next_step,
                    "parallel_agents": step.parallel_agents,
                }
                for name, step in self._steps.items()
            },
        }
    
    def __repr__(self) -> str:
        return f"Pipeline(name={self.name}, steps={len(self._steps)})"


# 기본 파이프라인 템플릿
def create_standard_pipeline(name: str = "standard") -> Pipeline:
    """표준 파이프라인 생성 (Planner → Executor → Writer → QA)"""
    return (
        Pipeline(name)
        .agent("plan", "planner", next_step="execute")
        .agent("execute", "executor", next_step="write")
        .agent("write", "writer", next_step="qa")
        .agent("qa", "qa", next_step="end")
        .end()
    )


def create_simple_pipeline(name: str = "simple") -> Pipeline:
    """간단한 파이프라인 (Executor만)"""
    return (
        Pipeline(name)
        .agent("execute", "executor", next_step="end")
        .end()
    )


def create_research_pipeline(name: str = "research") -> Pipeline:
    """연구 파이프라인 (Literature → Analysis → Writer)"""
    return (
        Pipeline(name)
        .agent("literature", "literature", next_step="analysis")
        .parallel("analysis", ["gis", "swmm"], next_step="write")
        .agent("write", "academic_writer", next_step="qa")
        .agent("qa", "qa", next_step="end")
        .end()
    )
