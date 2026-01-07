"""
MetaAgent - 최상위 오케스트레이터

이 파일의 책임:
- 프로젝트 기반 Agent 오케스트레이션
- 전체 실행 흐름 관리
- Agent 간 통신 조율
- 결과 집계 및 최종 출력 생성
"""

from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
import asyncio
import time

from prometheus.controller.agent_factory import AgentFactory
from prometheus.controller.router import Router, RouteDecision, RoutingStrategy
from prometheus.controller.lifecycle import LifecycleManager, AgentState, ProjectState
from prometheus.config.project_schema import ProjectConfig, AgentType
from prometheus.config.loader import ConfigLoader
from prometheus.agents.base import BaseAgent, AgentInput, AgentOutput
from prometheus.agents.planner_agent import ExecutionPlan, TaskStatus
from prometheus.llm.base import BaseLLMClient


class ExecutionMode(str, Enum):
    """실행 모드"""
    
    AUTO = "auto"           # 자동 (Router가 결정)
    SEQUENTIAL = "sequential"  # 순차 실행
    PLAN_BASED = "plan_based"  # 계획 기반 실행


class ProjectExecutionResult(BaseModel):
    """프로젝트 실행 결과"""
    
    project_id: str
    success: bool = True
    result: Any = None
    error: Optional[str] = None
    plan: Optional[ExecutionPlan] = None
    step_results: List[AgentOutput] = Field(default_factory=list)
    final_document: Optional[Any] = None
    quality_report: Optional[Any] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MetaAgentConfig(BaseModel):
    """MetaAgent 설정"""
    
    default_mode: ExecutionMode = ExecutionMode.AUTO
    enable_qa: bool = True
    enable_planning: bool = True
    max_iterations: int = 50
    timeout: float = 600.0


class MetaAgent:
    """
    최상위 오케스트레이터
    
    프로젝트 기반으로 여러 Agent를 조율하고
    전체 실행 흐름을 관리합니다.
    """
    
    def __init__(
        self,
        config: Optional[MetaAgentConfig] = None,
        agent_factory: Optional[AgentFactory] = None,
        router: Optional[Router] = None,
        lifecycle_manager: Optional[LifecycleManager] = None,
        config_loader: Optional[ConfigLoader] = None,
    ) -> None:
        """
        MetaAgent 초기화
        
        Args:
            config: MetaAgent 설정
            agent_factory: Agent 팩토리
            router: 라우터
            lifecycle_manager: 생명주기 관리자
            config_loader: 설정 로더
        """
        self.config = config or MetaAgentConfig()
        self._agent_factory = agent_factory or AgentFactory()
        self._router = router or Router()
        self._lifecycle = lifecycle_manager or LifecycleManager()
        self._config_loader = config_loader or ConfigLoader()
        
        # 프로젝트별 Agent 저장소
        self._project_agents: Dict[str, Dict[AgentType, BaseAgent]] = {}
        
        # 현재 실행 중인 프로젝트
        self._current_project: Optional[str] = None
    
    async def process_request(
        self,
        request: str,
        project_name: Optional[str] = None,
        mode: Optional[ExecutionMode] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ProjectExecutionResult:
        """
        요청 처리
        
        Args:
            request: 사용자 요청
            project_name: 프로젝트 이름 (None이면 기본 프로젝트)
            mode: 실행 모드
            context: 추가 컨텍스트
            
        Returns:
            실행 결과
        """
        start_time = time.time()
        mode = mode or self.config.default_mode
        
        # 프로젝트 로드 또는 생성
        project_config = await self._load_or_create_project(project_name)
        project_id = project_config.metadata.name
        
        # 프로젝트 상태 등록
        self._lifecycle.register_project(project_id)
        self._lifecycle.transition_project(project_id, ProjectState.LOADING)
        
        try:
            # Agent 생성
            agents = await self._setup_agents(project_config)
            self._project_agents[project_id] = agents
            
            self._lifecycle.transition_project(project_id, ProjectState.READY)
            self._lifecycle.transition_project(project_id, ProjectState.RUNNING)
            
            # 실행 모드 결정
            if mode == ExecutionMode.AUTO:
                route = await self._router.route(request, context)
                if route.requires_planning:
                    mode = ExecutionMode.PLAN_BASED
                else:
                    mode = ExecutionMode.SEQUENTIAL
            
            # 실행
            if mode == ExecutionMode.PLAN_BASED and self.config.enable_planning:
                result = await self._execute_with_plan(
                    request=request,
                    project_id=project_id,
                    agents=agents,
                    context=context,
                )
            else:
                result = await self._execute_sequential(
                    request=request,
                    project_id=project_id,
                    agents=agents,
                    context=context,
                )
            
            self._lifecycle.transition_project(project_id, ProjectState.COMPLETED)
            
            result.execution_time = time.time() - start_time
            return result
            
        except Exception as e:
            self._lifecycle.transition_project(project_id, ProjectState.FAILED)
            return ProjectExecutionResult(
                project_id=project_id,
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )
    
    async def _execute_with_plan(
        self,
        request: str,
        project_id: str,
        agents: Dict[AgentType, BaseAgent],
        context: Optional[Dict[str, Any]] = None,
    ) -> ProjectExecutionResult:
        """
        계획 기반 실행
        
        Args:
            request: 요청
            project_id: 프로젝트 ID
            agents: Agent 딕셔너리
            context: 컨텍스트
            
        Returns:
            실행 결과
        """
        step_results = []
        context = context or {}
        
        # 1. 계획 수립
        planner = agents.get(AgentType.PLANNER)
        if planner is None:
            raise ValueError("Planner agent not available")
        
        plan_input = AgentInput(task=request, context=context)
        plan_output = await planner.run(plan_input)
        
        if not plan_output.success:
            return ProjectExecutionResult(
                project_id=project_id,
                success=False,
                error=f"Planning failed: {plan_output.error}",
            )
        
        plan: ExecutionPlan = plan_output.result
        step_results.append(plan_output)
        
        # 2. 단계별 실행
        executor = agents.get(AgentType.EXECUTOR)
        accumulated_context = dict(context)
        accumulated_context["plan"] = plan.model_dump()
        
        iteration = 0
        while not plan.is_completed() and iteration < self.config.max_iterations:
            step = plan.get_next_step()
            if step is None:
                break
            
            # Agent 선택
            target_agent = agents.get(AgentType(step.agent_type))
            if target_agent is None:
                target_agent = executor
            
            # 단계 실행
            step_input = AgentInput(
                task=step.description,
                context={
                    "step": step.model_dump(),
                    "previous_results": accumulated_context,
                },
            )
            
            step_output = await target_agent.run(step_input)
            step_results.append(step_output)
            
            # 상태 업데이트
            if step_output.success:
                plan.update_step_status(step.step_id, TaskStatus.COMPLETED)
                accumulated_context[step.step_id] = step_output.result
            else:
                plan.update_step_status(step.step_id, TaskStatus.FAILED)
            
            iteration += 1
        
        # 3. 문서 작성 (Writer)
        final_document = None
        writer = agents.get(AgentType.WRITER)
        if writer:
            writer_input = AgentInput(
                task="실행 결과를 기반으로 보고서 작성",
                context={
                    "original_request": request,
                    "plan": plan.model_dump(),
                    "results": accumulated_context,
                    "title": f"프로젝트 {project_id} 결과 보고서",
                },
            )
            writer_output = await writer.run(writer_input)
            step_results.append(writer_output)
            if writer_output.success:
                final_document = writer_output.result
        
        # 4. 품질 검토 (QA)
        quality_report = None
        if self.config.enable_qa:
            qa = agents.get(AgentType.QA)
            if qa and final_document:
                qa_input = AgentInput(
                    task=str(final_document.content) if hasattr(final_document, 'content') else str(final_document),
                    context={"original_request": request},
                )
                qa_output = await qa.run(qa_input)
                step_results.append(qa_output)
                if qa_output.success:
                    quality_report = qa_output.result
        
        return ProjectExecutionResult(
            project_id=project_id,
            success=plan.is_completed(),
            result=accumulated_context,
            plan=plan,
            step_results=step_results,
            final_document=final_document,
            quality_report=quality_report,
        )
    
    async def _execute_sequential(
        self,
        request: str,
        project_id: str,
        agents: Dict[AgentType, BaseAgent],
        context: Optional[Dict[str, Any]] = None,
    ) -> ProjectExecutionResult:
        """
        순차 실행 (단순 요청)
        
        Args:
            request: 요청
            project_id: 프로젝트 ID
            agents: Agent 딕셔너리
            context: 컨텍스트
            
        Returns:
            실행 결과
        """
        step_results = []
        context = context or {}
        
        # 라우팅
        route = await self._router.route(request, context)
        target_agent = agents.get(route.target_agent)
        
        if target_agent is None:
            # Fallback to executor
            target_agent = agents.get(AgentType.EXECUTOR)
        
        if target_agent is None:
            return ProjectExecutionResult(
                project_id=project_id,
                success=False,
                error="No suitable agent found",
            )
        
        # 실행
        agent_input = AgentInput(task=request, context=context)
        agent_output = await target_agent.run(agent_input)
        step_results.append(agent_output)
        
        # QA (선택적)
        quality_report = None
        if self.config.enable_qa and agent_output.success:
            qa = agents.get(AgentType.QA)
            if qa:
                qa_input = AgentInput(
                    task=str(agent_output.result),
                    context={"original_request": request},
                )
                qa_output = await qa.run(qa_input)
                step_results.append(qa_output)
                if qa_output.success:
                    quality_report = qa_output.result
        
        return ProjectExecutionResult(
            project_id=project_id,
            success=agent_output.success,
            result=agent_output.result,
            error=agent_output.error,
            step_results=step_results,
            quality_report=quality_report,
        )
    
    async def _load_or_create_project(
        self,
        project_name: Optional[str],
    ) -> ProjectConfig:
        """
        프로젝트 로드 또는 생성
        
        Args:
            project_name: 프로젝트 이름
            
        Returns:
            프로젝트 설정
        """
        if project_name and self._config_loader.project_exists(project_name):
            return self._config_loader.load_project(project_name)
        
        # 기본 프로젝트 생성
        from prometheus.config.project_schema import (
            ProjectMetadata,
            AgentConfig as ProjAgentConfig,
            ToolConfig,
            LLMProviderConfig,
        )
        
        name = project_name or f"temp_project_{int(time.time())}"
        
        return ProjectConfig(
            metadata=ProjectMetadata(
                name=name,
                description="Auto-generated project",
            ),
            agents=[
                ProjAgentConfig(agent_type=AgentType.PLANNER),
                ProjAgentConfig(agent_type=AgentType.EXECUTOR),
                ProjAgentConfig(agent_type=AgentType.WRITER),
                ProjAgentConfig(agent_type=AgentType.QA),
            ],
        )
    
    async def _setup_agents(
        self,
        project_config: ProjectConfig,
    ) -> Dict[AgentType, BaseAgent]:
        """
        Agent 설정
        
        Args:
            project_config: 프로젝트 설정
            
        Returns:
            Agent 딕셔너리
        """
        agents = self._agent_factory.create_all_agents(
            project_config=project_config,
            auto_bind_llm=True,
            auto_bind_tools=True,
        )
        
        # Agent 상태 등록
        for agent_type, agent in agents.items():
            agent_id = f"{project_config.metadata.name}_{agent_type.value}"
            self._lifecycle.register_agent(agent_id)
            self._lifecycle.transition_agent(agent_id, AgentState.INITIALIZED)
            self._lifecycle.transition_agent(agent_id, AgentState.IDLE)
        
        # Router에 LLM 바인딩
        if AgentType.PLANNER in agents:
            planner_llm = agents[AgentType.PLANNER].llm
            if planner_llm:
                self._router.bind_llm(planner_llm)
        
        return agents
    
    def create_project(
        self,
        project_name: str,
        description: str = "",
        request: Optional[str] = None,
    ) -> str:
        """
        새 프로젝트 생성
        
        Args:
            project_name: 프로젝트 이름
            description: 설명
            request: 초기 요청
            
        Returns:
            생성된 프로젝트 경로
        """
        path = self._config_loader.create_project(
            project_name=project_name,
            request=request,
        )
        return str(path)
    
    def list_projects(self) -> List[str]:
        """프로젝트 목록"""
        return self._config_loader.list_projects()
    
    def get_project_status(
        self,
        project_name: str,
    ) -> Optional[ProjectState]:
        """프로젝트 상태 조회"""
        return self._lifecycle.get_project_state(project_name)
    
    def get_agents_status(
        self,
        project_name: str,
    ) -> Dict[str, AgentState]:
        """프로젝트의 Agent 상태 조회"""
        all_agents = self._lifecycle.list_agents()
        return {
            k: v for k, v in all_agents.items()
            if k.startswith(f"{project_name}_")
        }
    
    def register_tool(
        self,
        name: str,
        tool: Any,
    ) -> None:
        """Tool 등록"""
        self._agent_factory.register_tool(name, tool)
    
    def set_default_llm(
        self,
        llm: BaseLLMClient,
    ) -> None:
        """기본 LLM 설정"""
        self._router.bind_llm(llm)


# 편의 함수
async def run_project(
    request: str,
    project_name: Optional[str] = None,
    **kwargs,
) -> ProjectExecutionResult:
    """
    프로젝트 실행 편의 함수
    
    Args:
        request: 요청
        project_name: 프로젝트 이름
        **kwargs: 추가 인자
        
    Returns:
        실행 결과
    """
    meta_agent = MetaAgent()
    return await meta_agent.process_request(
        request=request,
        project_name=project_name,
        **kwargs,
    )
