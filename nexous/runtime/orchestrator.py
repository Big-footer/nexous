"""
NEXOUS Runtime - Orchestrator

Agent 실행을 오케스트레이션합니다.

플랫폼 책임:
- Agent 실행 순서 조율
- 실행 컨텍스트 관리
- 결과 집계
- 에러 처리 및 복구

주의: Orchestrator는 "언제, 어떤 순서로" 실행할지만 결정합니다.
"무엇을" 실행할지는 Agent가 결정합니다.
"""

from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from datetime import datetime
import asyncio
import logging

from nexous.core.lifecycle import LifecycleManager, AgentState, ProjectState, get_lifecycle_manager
from nexous.core.trace import Trace, TraceStore, create_trace, get_trace_store
from nexous.factory.agent_factory import AgentFactory, AgentInstance, get_agent_factory

logger = logging.getLogger(__name__)


class ExecutionMode(str, Enum):
    """실행 모드"""
    SEQUENTIAL = "sequential"   # 순차 실행
    PARALLEL = "parallel"       # 병렬 실행
    PIPELINE = "pipeline"       # 파이프라인 (이전 결과가 다음 입력)


class ExecutionResult:
    """실행 결과"""
    
    def __init__(
        self,
        project_id: str,
        success: bool = True,
        results: Dict[str, Any] = None,
        error: Optional[str] = None,
        trace_id: Optional[str] = None,
    ):
        self.project_id = project_id
        self.success = success
        self.results = results or {}
        self.error = error
        self.trace_id = trace_id
        self.completed_at = datetime.now()
    
    def get_agent_result(self, agent_name: str) -> Optional[Any]:
        return self.results.get(agent_name)


class Orchestrator:
    """
    Orchestrator (NEXOUS 플랫폼 핵심)
    
    Agent 실행을 조율합니다.
    Orchestrator는 실행 "파이프라인"만 관리하고,
    실제 작업은 Agent가 수행합니다.
    """
    
    def __init__(
        self,
        factory: Optional[AgentFactory] = None,
        lifecycle: Optional[LifecycleManager] = None,
        trace_store: Optional[TraceStore] = None,
    ):
        self._factory = factory or get_agent_factory()
        self._lifecycle = lifecycle or get_lifecycle_manager()
        self._trace_store = trace_store or get_trace_store()
        
        # 실행 중인 프로젝트
        self._running_projects: Dict[str, Trace] = {}
        
        logger.info("[NEXOUS] Orchestrator initialized")
    
    async def execute(
        self,
        project_id: str,
        request: str,
        agents: Dict[str, AgentInstance],
        mode: ExecutionMode = ExecutionMode.PIPELINE,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Agent 실행 오케스트레이션
        
        Args:
            project_id: 프로젝트 ID
            request: 사용자 요청
            agents: 실행할 Agent 딕셔너리
            mode: 실행 모드
            context: 초기 컨텍스트
        
        Returns:
            ExecutionResult
        """
        # 1. Trace 생성
        trace = create_trace(
            project_id=project_id,
            project_name=project_id,
            request=request,
        )
        self._running_projects[project_id] = trace
        
        # 2. Project 상태 전이
        self._lifecycle.register_project(project_id)
        self._lifecycle.transition_project(project_id, ProjectState.LOADING)
        self._lifecycle.transition_project(project_id, ProjectState.READY)
        self._lifecycle.transition_project(project_id, ProjectState.RUNNING)
        
        try:
            # 3. 실행 모드에 따라 실행
            if mode == ExecutionMode.SEQUENTIAL:
                results = await self._execute_sequential(agents, request, context, trace)
            elif mode == ExecutionMode.PARALLEL:
                results = await self._execute_parallel(agents, request, context, trace)
            elif mode == ExecutionMode.PIPELINE:
                results = await self._execute_pipeline(agents, request, context, trace)
            else:
                raise ValueError(f"Unknown execution mode: {mode}")
            
            # 4. 완료 처리
            trace.complete(outputs=results)
            self._lifecycle.transition_project(project_id, ProjectState.COMPLETED)
            
            result = ExecutionResult(
                project_id=project_id,
                success=True,
                results=results,
                trace_id=trace.trace_id,
            )
            
        except Exception as e:
            # 5. 에러 처리
            import traceback
            trace.fail(str(e), traceback.format_exc())
            self._lifecycle.transition_project(project_id, ProjectState.FAILED)
            
            result = ExecutionResult(
                project_id=project_id,
                success=False,
                error=str(e),
                trace_id=trace.trace_id,
            )
            logger.error(f"[NEXOUS] Execution failed: {project_id} - {e}")
        
        finally:
            # 6. Trace 저장
            self._trace_store.save(trace)
            del self._running_projects[project_id]
        
        return result
    
    async def _execute_sequential(
        self,
        agents: Dict[str, AgentInstance],
        request: str,
        context: Optional[Dict],
        trace: Trace,
    ) -> Dict[str, Any]:
        """순차 실행"""
        results = {}
        current_input = {"request": request, "context": context or {}}
        
        for name, agent in agents.items():
            # Agent 상태 전이
            self._lifecycle.transition_agent(agent.agent_id, AgentState.RUNNING)
            trace.start_agent(name, current_input)
            
            try:
                # Agent 실행 (실제 작업은 Agent가 수행)
                result = await self._invoke_agent(agent, current_input)
                results[name] = result
                
                trace.finish_agent(name, {"result": str(result)[:500]})
                self._lifecycle.transition_agent(agent.agent_id, AgentState.IDLE)
                
            except Exception as e:
                trace.finish_agent(name, error=str(e))
                self._lifecycle.transition_agent(agent.agent_id, AgentState.FAILED)
                raise
        
        return results
    
    async def _execute_parallel(
        self,
        agents: Dict[str, AgentInstance],
        request: str,
        context: Optional[Dict],
        trace: Trace,
    ) -> Dict[str, Any]:
        """병렬 실행"""
        tasks = []
        agent_names = []
        
        input_data = {"request": request, "context": context or {}}
        
        for name, agent in agents.items():
            self._lifecycle.transition_agent(agent.agent_id, AgentState.RUNNING)
            trace.start_agent(name, input_data)
            
            task = self._invoke_agent(agent, input_data)
            tasks.append(task)
            agent_names.append(name)
        
        # 모든 Agent 병렬 실행
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        results = {}
        for name, result in zip(agent_names, results_list):
            agent = agents[name]
            
            if isinstance(result, Exception):
                trace.finish_agent(name, error=str(result))
                self._lifecycle.transition_agent(agent.agent_id, AgentState.FAILED)
                results[name] = {"error": str(result)}
            else:
                trace.finish_agent(name, {"result": str(result)[:500]})
                self._lifecycle.transition_agent(agent.agent_id, AgentState.IDLE)
                results[name] = result
        
        return results
    
    async def _execute_pipeline(
        self,
        agents: Dict[str, AgentInstance],
        request: str,
        context: Optional[Dict],
        trace: Trace,
    ) -> Dict[str, Any]:
        """파이프라인 실행 (이전 결과가 다음 입력)"""
        results = {}
        accumulated_context = {"request": request, **(context or {})}
        
        for name, agent in agents.items():
            self._lifecycle.transition_agent(agent.agent_id, AgentState.RUNNING)
            
            # 이전 결과들을 컨텍스트에 추가
            current_input = {
                "request": request,
                "context": accumulated_context,
                "previous_results": results.copy(),
            }
            
            trace.start_agent(name, {"keys": list(current_input.keys())})
            
            try:
                result = await self._invoke_agent(agent, current_input)
                results[name] = result
                
                # 다음 Agent를 위해 컨텍스트 업데이트
                if isinstance(result, dict):
                    accumulated_context.update(result)
                else:
                    accumulated_context[name] = result
                
                trace.finish_agent(name, {"result": str(result)[:500]})
                self._lifecycle.transition_agent(agent.agent_id, AgentState.IDLE)
                
            except Exception as e:
                trace.finish_agent(name, error=str(e))
                self._lifecycle.transition_agent(agent.agent_id, AgentState.FAILED)
                raise
        
        return results
    
    async def _invoke_agent(self, agent: AgentInstance, input_data: Dict) -> Any:
        """Agent 호출 (비동기)"""
        if hasattr(agent, 'ainvoke'):
            return await agent.ainvoke(input_data)
        else:
            # 동기 호출을 비동기로 래핑
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, agent.invoke, input_data)
    
    def get_running_projects(self) -> List[str]:
        """실행 중인 프로젝트 목록"""
        return list(self._running_projects.keys())
    
    def get_trace(self, project_id: str) -> Optional[Trace]:
        """실행 중인 프로젝트의 Trace 조회"""
        return self._running_projects.get(project_id)


# 싱글톤 인스턴스
_orchestrator: Optional[Orchestrator] = None

def get_orchestrator() -> Orchestrator:
    """전역 Orchestrator 반환"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
