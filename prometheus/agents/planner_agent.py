"""
PlannerAgent - 계획 수립 Agent

이 파일의 책임:
- 사용자 요청 분석
- 실행 계획 수립
- 작업 분해 (Task Decomposition)
- 의존성 분석
"""

from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field
import json

from prometheus.agents.base import (
    BaseAgent,
    AgentConfig,
    AgentInput,
    AgentOutput,
    AgentState,
)
from prometheus.llm.base import Message, MessageRole


class TaskPriority(str, Enum):
    """작업 우선순위"""
    
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    """작업 상태"""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlanStep(BaseModel):
    """계획 단계"""
    
    step_id: str
    title: str
    description: str
    agent_type: str = "executor"
    tools_required: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    estimated_time: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecutionPlan(BaseModel):
    """실행 계획"""
    
    plan_id: str
    title: str
    description: str
    steps: List[PlanStep] = Field(default_factory=list)
    total_steps: int = 0
    estimated_total_time: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def model_post_init(self, __context: Any) -> None:
        """초기화 후 처리"""
        self.total_steps = len(self.steps)
    
    def get_next_step(self) -> Optional[PlanStep]:
        """다음 실행 단계 조회"""
        for step in self.steps:
            if step.status == TaskStatus.PENDING:
                # 의존성 확인
                deps_completed = all(
                    self.get_step(dep_id).status == TaskStatus.COMPLETED
                    for dep_id in step.dependencies
                    if self.get_step(dep_id) is not None
                )
                if deps_completed:
                    return step
        return None
    
    def get_step(self, step_id: str) -> Optional[PlanStep]:
        """단계 조회"""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None
    
    def update_step_status(self, step_id: str, status: TaskStatus) -> bool:
        """단계 상태 업데이트"""
        step = self.get_step(step_id)
        if step:
            step.status = status
            return True
        return False
    
    def is_completed(self) -> bool:
        """계획 완료 여부"""
        return all(
            step.status in [TaskStatus.COMPLETED, TaskStatus.SKIPPED]
            for step in self.steps
        )
    
    def get_progress(self) -> float:
        """진행률 (0.0 ~ 1.0)"""
        if not self.steps:
            return 1.0
        completed = sum(
            1 for step in self.steps
            if step.status in [TaskStatus.COMPLETED, TaskStatus.SKIPPED]
        )
        return completed / len(self.steps)


class PlannerConfig(AgentConfig):
    """Planner 설정"""
    
    name: str = "PlannerAgent"
    max_steps: int = 20
    include_dependencies: bool = True
    include_time_estimates: bool = False


class PlannerAgent(BaseAgent):
    """
    계획 수립 Agent
    
    사용자 요청을 분석하고 실행 가능한 계획을 수립합니다.
    작업을 단계별로 분해하고 의존성을 분석합니다.
    """
    
    agent_type: str = "planner"
    
    PLANNING_PROMPT = """You are a planning expert. Your task is to analyze the user's request and create a detailed execution plan.

Create a structured plan with the following requirements:
1. Break down the task into clear, actionable steps
2. Identify which agent type should handle each step (planner, executor, writer, qa)
3. List any tools required for each step
4. Identify dependencies between steps
5. Assign priority levels (high, medium, low)

Available tools: {available_tools}

Respond with a JSON object in this exact format:
{{
    "plan_id": "plan_<unique_id>",
    "title": "Plan title",
    "description": "Brief description of the overall plan",
    "steps": [
        {{
            "step_id": "step_1",
            "title": "Step title",
            "description": "Detailed description of what to do",
            "agent_type": "executor",
            "tools_required": ["tool_name"],
            "dependencies": [],
            "priority": "high"
        }}
    ]
}}

User Request: {request}

Context: {context}"""

    def __init__(
        self,
        config: Optional[PlannerConfig] = None,
        **kwargs: Any,
    ) -> None:
        """
        PlannerAgent 초기화
        
        Args:
            config: Planner 설정
            **kwargs: 추가 인자
        """
        super().__init__(config=config or PlannerConfig(), **kwargs)
    
    def _default_system_prompt(self) -> str:
        """기본 시스템 프롬프트"""
        return """You are an expert planning agent. Your role is to:
1. Analyze user requests thoroughly
2. Create detailed, actionable execution plans
3. Break complex tasks into manageable steps
4. Identify dependencies and optimal execution order
5. Select appropriate tools and agents for each step

Always respond with valid JSON when creating plans."""
    
    async def run(
        self,
        input: AgentInput,
    ) -> AgentOutput:
        """
        계획 수립 실행
        
        Args:
            input: Agent 입력
            
        Returns:
            Agent 출력 (ExecutionPlan 포함)
        """
        import time
        start_time = time.time()
        
        self._set_state(AgentState.RUNNING)
        
        try:
            # 계획 수립
            plan = await self.create_plan(
                request=input.task,
                context=input.context,
            )
            
            execution_time = time.time() - start_time
            self._set_state(AgentState.COMPLETED)
            
            return AgentOutput.success_output(
                result=plan,
                messages=self._messages.copy(),
                execution_time=execution_time,
                metadata={"plan_id": plan.plan_id},
            )
            
        except Exception as e:
            self._set_state(AgentState.FAILED)
            return AgentOutput.error_output(
                error=str(e),
                messages=self._messages.copy(),
            )
    
    async def create_plan(
        self,
        request: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionPlan:
        """
        실행 계획 생성
        
        Args:
            request: 사용자 요청
            context: 추가 컨텍스트
            
        Returns:
            실행 계획
        """
        # 사용 가능한 Tool 목록
        available_tools = list(self._tools.keys()) if self._tools else ["none"]
        
        # 프롬프트 생성
        prompt = self.PLANNING_PROMPT.format(
            request=request,
            context=json.dumps(context or {}, ensure_ascii=False),
            available_tools=", ".join(available_tools),
        )
        
        # 메시지 구성
        messages = [
            Message.system(self.get_system_prompt()),
            Message.user(prompt),
        ]
        
        # LLM 호출
        response = await self._call_llm(messages, temperature=0.3)
        
        # 응답 저장
        self._add_message(Message.user(prompt))
        self._add_message(Message.assistant(response.content))
        
        # JSON 파싱
        plan_data = self._parse_plan_response(response.content)
        
        # ExecutionPlan 생성
        return self._create_execution_plan(plan_data)
    
    async def decompose_task(
        self,
        task: str,
        max_depth: int = 2,
    ) -> List[PlanStep]:
        """
        작업 분해
        
        Args:
            task: 분해할 작업
            max_depth: 최대 분해 깊이
            
        Returns:
            분해된 단계 목록
        """
        prompt = f"""Break down the following task into smaller, actionable steps.
Each step should be specific and executable.

Task: {task}

Respond with a JSON array of steps:
[
    {{
        "step_id": "step_1",
        "title": "Step title",
        "description": "What to do",
        "agent_type": "executor"
    }}
]"""
        
        messages = [
            Message.system(self.get_system_prompt()),
            Message.user(prompt),
        ]
        
        response = await self._call_llm(messages, temperature=0.3)
        
        # JSON 파싱
        try:
            steps_data = json.loads(self._extract_json(response.content))
            return [
                PlanStep(
                    step_id=s.get("step_id", f"step_{i}"),
                    title=s.get("title", ""),
                    description=s.get("description", ""),
                    agent_type=s.get("agent_type", "executor"),
                )
                for i, s in enumerate(steps_data)
            ]
        except json.JSONDecodeError:
            return []
    
    async def analyze_dependencies(
        self,
        steps: List[PlanStep],
    ) -> List[PlanStep]:
        """
        단계 간 의존성 분석
        
        Args:
            steps: 단계 목록
            
        Returns:
            의존성이 추가된 단계 목록
        """
        if len(steps) <= 1:
            return steps
        
        steps_info = [
            {"step_id": s.step_id, "title": s.title, "description": s.description}
            for s in steps
        ]
        
        prompt = f"""Analyze the dependencies between these steps.
For each step, identify which other steps must be completed first.

Steps:
{json.dumps(steps_info, indent=2, ensure_ascii=False)}

Respond with a JSON object mapping step_id to list of dependency step_ids:
{{
    "step_1": [],
    "step_2": ["step_1"],
    "step_3": ["step_1", "step_2"]
}}"""
        
        messages = [
            Message.system(self.get_system_prompt()),
            Message.user(prompt),
        ]
        
        response = await self._call_llm(messages, temperature=0.2)
        
        try:
            deps_data = json.loads(self._extract_json(response.content))
            for step in steps:
                if step.step_id in deps_data:
                    step.dependencies = deps_data[step.step_id]
        except json.JSONDecodeError:
            pass
        
        return steps
    
    def _parse_plan_response(self, response: str) -> Dict[str, Any]:
        """
        LLM 응답에서 계획 데이터 파싱
        
        Args:
            response: LLM 응답
            
        Returns:
            계획 데이터 딕셔너리
        """
        json_str = self._extract_json(response)
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            # 기본 계획 반환
            return {
                "plan_id": "plan_fallback",
                "title": "Execution Plan",
                "description": "Auto-generated plan",
                "steps": [
                    {
                        "step_id": "step_1",
                        "title": "Execute Request",
                        "description": response[:500],
                        "agent_type": "executor",
                    }
                ],
            }
    
    def _extract_json(self, text: str) -> str:
        """
        텍스트에서 JSON 추출
        
        Args:
            text: 원본 텍스트
            
        Returns:
            JSON 문자열
        """
        # JSON 블록 추출 시도
        import re
        
        # ```json ... ``` 패턴
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            return json_match.group(1).strip()
        
        # { ... } 패턴
        brace_match = re.search(r'(\{[\s\S]*\})', text)
        if brace_match:
            return brace_match.group(1)
        
        # [ ... ] 패턴
        bracket_match = re.search(r'(\[[\s\S]*\])', text)
        if bracket_match:
            return bracket_match.group(1)
        
        return text
    
    def _create_execution_plan(self, data: Dict[str, Any]) -> ExecutionPlan:
        """
        ExecutionPlan 객체 생성
        
        Args:
            data: 계획 데이터
            
        Returns:
            ExecutionPlan 인스턴스
        """
        steps = []
        for i, step_data in enumerate(data.get("steps", [])):
            steps.append(PlanStep(
                step_id=step_data.get("step_id", f"step_{i+1}"),
                title=step_data.get("title", f"Step {i+1}"),
                description=step_data.get("description", ""),
                agent_type=step_data.get("agent_type", "executor"),
                tools_required=step_data.get("tools_required", []),
                dependencies=step_data.get("dependencies", []),
                priority=TaskPriority(step_data.get("priority", "medium")),
                metadata=step_data.get("metadata", {}),
            ))
        
        return ExecutionPlan(
            plan_id=data.get("plan_id", "plan_default"),
            title=data.get("title", "Execution Plan"),
            description=data.get("description", ""),
            steps=steps,
            metadata=data.get("metadata", {}),
        )
    
    def validate_plan(self, plan: ExecutionPlan) -> List[str]:
        """
        계획 유효성 검증
        
        Args:
            plan: 검증할 계획
            
        Returns:
            오류 메시지 목록 (빈 목록이면 유효)
        """
        errors = []
        
        # 단계 ID 중복 검사
        step_ids = [s.step_id for s in plan.steps]
        if len(step_ids) != len(set(step_ids)):
            errors.append("Duplicate step IDs found")
        
        # 순환 의존성 검사
        for step in plan.steps:
            visited = set()
            if self._has_circular_dependency(step.step_id, plan, visited):
                errors.append(f"Circular dependency detected for step: {step.step_id}")
        
        # 존재하지 않는 의존성 검사
        for step in plan.steps:
            for dep_id in step.dependencies:
                if dep_id not in step_ids:
                    errors.append(f"Step {step.step_id} depends on non-existent step: {dep_id}")
        
        return errors
    
    def _has_circular_dependency(
        self,
        step_id: str,
        plan: ExecutionPlan,
        visited: set,
    ) -> bool:
        """순환 의존성 검사"""
        if step_id in visited:
            return True
        
        visited.add(step_id)
        step = plan.get_step(step_id)
        
        if step:
            for dep_id in step.dependencies:
                if self._has_circular_dependency(dep_id, plan, visited.copy()):
                    return True
        
        return False
