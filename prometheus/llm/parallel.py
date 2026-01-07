"""
PROMETHEUS Parallel Execution Support

독립적인 작업의 병렬 실행을 지원합니다.
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable, TypeVar, Coroutine
from dataclasses import dataclass
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class ParallelResult:
    """병렬 실행 결과"""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class ParallelExecutionSummary:
    """병렬 실행 요약"""
    total_tasks: int
    success_count: int
    fail_count: int
    total_time: float
    results: List[ParallelResult]
    
    @property
    def success_rate(self) -> float:
        """성공률"""
        if self.total_tasks == 0:
            return 0.0
        return self.success_count / self.total_tasks * 100


class ParallelExecutor:
    """
    병렬 실행기
    
    독립적인 작업을 병렬로 실행합니다.
    ThreadPoolExecutor와 asyncio를 모두 지원합니다.
    
    Example:
        ```python
        executor = ParallelExecutor(max_workers=4)
        
        # 동기 작업 병렬 실행
        tasks = [
            ("task1", lambda: slow_function(1)),
            ("task2", lambda: slow_function(2)),
        ]
        results = executor.execute_sync(tasks)
        
        # 비동기 작업 병렬 실행
        async_tasks = [
            ("task1", slow_async_function(1)),
            ("task2", slow_async_function(2)),
        ]
        results = await executor.execute_async(async_tasks)
        ```
    """
    
    def __init__(self, max_workers: int = 4):
        """
        초기화
        
        Args:
            max_workers: 최대 워커 수
        """
        self.max_workers = max_workers
    
    def execute_sync(
        self,
        tasks: List[tuple[str, Callable]],
        timeout: Optional[float] = None,
    ) -> ParallelExecutionSummary:
        """
        동기 작업 병렬 실행
        
        Args:
            tasks: (task_id, callable) 튜플 리스트
            timeout: 전체 타임아웃 (초)
        
        Returns:
            ParallelExecutionSummary
        """
        start_time = datetime.now()
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 작업 제출
            future_to_task = {
                executor.submit(task_fn): task_id
                for task_id, task_fn in tasks
            }
            
            # 결과 수집
            for future in as_completed(future_to_task, timeout=timeout):
                task_id = future_to_task[future]
                task_start = datetime.now()
                
                try:
                    result = future.result()
                    exec_time = (datetime.now() - task_start).total_seconds()
                    
                    results.append(ParallelResult(
                        task_id=task_id,
                        success=True,
                        result=result,
                        execution_time=exec_time,
                    ))
                    logger.debug(f"✅ {task_id} 완료 ({exec_time:.2f}s)")
                    
                except Exception as e:
                    exec_time = (datetime.now() - task_start).total_seconds()
                    
                    results.append(ParallelResult(
                        task_id=task_id,
                        success=False,
                        error=str(e),
                        execution_time=exec_time,
                    ))
                    logger.warning(f"❌ {task_id} 실패: {e}")
        
        total_time = (datetime.now() - start_time).total_seconds()
        success_count = sum(1 for r in results if r.success)
        
        return ParallelExecutionSummary(
            total_tasks=len(tasks),
            success_count=success_count,
            fail_count=len(tasks) - success_count,
            total_time=total_time,
            results=results,
        )
    
    async def execute_async(
        self,
        tasks: List[tuple[str, Coroutine]],
        timeout: Optional[float] = None,
    ) -> ParallelExecutionSummary:
        """
        비동기 작업 병렬 실행
        
        Args:
            tasks: (task_id, coroutine) 튜플 리스트
            timeout: 전체 타임아웃 (초)
        
        Returns:
            ParallelExecutionSummary
        """
        start_time = datetime.now()
        results = []
        
        async def execute_task(task_id: str, coro: Coroutine) -> ParallelResult:
            task_start = datetime.now()
            try:
                result = await coro
                exec_time = (datetime.now() - task_start).total_seconds()
                
                logger.debug(f"✅ {task_id} 완료 ({exec_time:.2f}s)")
                return ParallelResult(
                    task_id=task_id,
                    success=True,
                    result=result,
                    execution_time=exec_time,
                )
            except Exception as e:
                exec_time = (datetime.now() - task_start).total_seconds()
                
                logger.warning(f"❌ {task_id} 실패: {e}")
                return ParallelResult(
                    task_id=task_id,
                    success=False,
                    error=str(e),
                    execution_time=exec_time,
                )
        
        # 모든 작업 동시 실행
        task_coros = [execute_task(task_id, coro) for task_id, coro in tasks]
        
        if timeout:
            results = await asyncio.wait_for(
                asyncio.gather(*task_coros, return_exceptions=True),
                timeout=timeout,
            )
        else:
            results = await asyncio.gather(*task_coros, return_exceptions=True)
        
        # Exception 결과 처리
        processed_results = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                task_id = tasks[i][0]
                processed_results.append(ParallelResult(
                    task_id=task_id,
                    success=False,
                    error=str(r),
                ))
            else:
                processed_results.append(r)
        
        total_time = (datetime.now() - start_time).total_seconds()
        success_count = sum(1 for r in processed_results if r.success)
        
        return ParallelExecutionSummary(
            total_tasks=len(tasks),
            success_count=success_count,
            fail_count=len(tasks) - success_count,
            total_time=total_time,
            results=processed_results,
        )


# =============================================================================
# Agent 병렬 실행 유틸리티
# =============================================================================

async def run_agents_parallel(
    agents: List[tuple[str, Any, str]],
    max_workers: int = 4,
) -> Dict[str, Any]:
    """
    여러 Agent를 병렬로 실행
    
    Args:
        agents: (agent_name, agent, input) 튜플 리스트
        max_workers: 최대 워커 수
    
    Returns:
        {agent_name: result} 딕셔너리
    
    Example:
        ```python
        results = await run_agents_parallel([
            ("planner1", planner_agent, "요청 1"),
            ("planner2", planner_agent, "요청 2"),
        ])
        ```
    """
    executor = ParallelExecutor(max_workers=max_workers)
    
    async def run_agent(agent, input_data):
        if asyncio.iscoroutinefunction(agent.ainvoke):
            return await agent.ainvoke(input_data)
        else:
            return agent.invoke(input_data)
    
    tasks = [
        (name, run_agent(agent, input_data))
        for name, agent, input_data in agents
    ]
    
    summary = await executor.execute_async(tasks)
    
    return {
        r.task_id: r.result if r.success else {"error": r.error}
        for r in summary.results
    }


def run_tools_parallel(
    tool_calls: List[tuple[str, Callable, Dict]],
    max_workers: int = 4,
) -> Dict[str, Any]:
    """
    여러 Tool을 병렬로 실행
    
    Args:
        tool_calls: (tool_name, tool_fn, args) 튜플 리스트
        max_workers: 최대 워커 수
    
    Returns:
        {tool_name: result} 딕셔너리
    
    Example:
        ```python
        results = run_tools_parallel([
            ("python1", python_exec, {"code": "print(1)"}),
            ("python2", python_exec, {"code": "print(2)"}),
        ])
        ```
    """
    executor = ParallelExecutor(max_workers=max_workers)
    
    tasks = [
        (name, lambda fn=fn, args=args: fn.invoke(args) if hasattr(fn, 'invoke') else fn(**args))
        for name, fn, args in tool_calls
    ]
    
    summary = executor.execute_sync(tasks)
    
    return {
        r.task_id: r.result if r.success else {"error": r.error}
        for r in summary.results
    }


# =============================================================================
# 배치 처리 유틸리티
# =============================================================================

async def batch_invoke_async(
    agent,
    inputs: List[str],
    batch_size: int = 5,
    delay: float = 0.1,
) -> List[Any]:
    """
    Agent를 배치로 실행 (Rate limiting 고려)
    
    Args:
        agent: Agent 인스턴스
        inputs: 입력 리스트
        batch_size: 배치 크기
        delay: 배치 간 대기 시간 (초)
    
    Returns:
        결과 리스트
    """
    results = []
    
    for i in range(0, len(inputs), batch_size):
        batch = inputs[i:i + batch_size]
        
        # 배치 병렬 실행
        if hasattr(agent, 'abatch'):
            batch_results = await agent.abatch(batch)
        else:
            batch_results = [await agent.ainvoke(inp) for inp in batch]
        
        results.extend(batch_results)
        
        # Rate limiting
        if i + batch_size < len(inputs):
            await asyncio.sleep(delay)
    
    return results


def batch_invoke_sync(
    agent,
    inputs: List[str],
    batch_size: int = 5,
) -> List[Any]:
    """
    Agent를 배치로 실행 (동기 버전)
    
    Args:
        agent: Agent 인스턴스
        inputs: 입력 리스트
        batch_size: 배치 크기
    
    Returns:
        결과 리스트
    """
    results = []
    
    for i in range(0, len(inputs), batch_size):
        batch = inputs[i:i + batch_size]
        
        if hasattr(agent, 'batch'):
            batch_results = agent.batch(batch)
        else:
            batch_results = [agent.invoke(inp) for inp in batch]
        
        results.extend(batch_results)
    
    return results
