"""
병렬 실행 테스트
"""

import pytest
import asyncio
import time
from prometheus.llm.parallel import (
    ParallelExecutor,
    ParallelResult,
    ParallelExecutionSummary,
    run_tools_parallel,
)


class TestParallelResult:
    """ParallelResult 테스트"""
    
    def test_result_creation(self):
        """결과 생성"""
        result = ParallelResult(
            task_id="task1",
            success=True,
            result="value",
            execution_time=1.5,
        )
        assert result.task_id == "task1"
        assert result.success == True
        assert result.result == "value"
    
    def test_failed_result(self):
        """실패 결과"""
        result = ParallelResult(
            task_id="task2",
            success=False,
            error="Something went wrong",
        )
        assert result.success == False
        assert result.error == "Something went wrong"


class TestParallelExecutionSummary:
    """ParallelExecutionSummary 테스트"""
    
    def test_success_rate(self):
        """성공률 계산"""
        summary = ParallelExecutionSummary(
            total_tasks=10,
            success_count=8,
            fail_count=2,
            total_time=5.0,
            results=[],
        )
        assert summary.success_rate == 80.0
    
    def test_success_rate_zero_tasks(self):
        """작업 없을 때 성공률"""
        summary = ParallelExecutionSummary(
            total_tasks=0,
            success_count=0,
            fail_count=0,
            total_time=0.0,
            results=[],
        )
        assert summary.success_rate == 0.0


class TestParallelExecutor:
    """ParallelExecutor 테스트"""
    
    def test_executor_creation(self):
        """실행기 생성"""
        executor = ParallelExecutor(max_workers=4)
        assert executor.max_workers == 4
    
    def test_execute_sync_success(self):
        """동기 실행 성공"""
        executor = ParallelExecutor(max_workers=2)
        
        tasks = [
            ("task1", lambda: 1 + 1),
            ("task2", lambda: 2 + 2),
            ("task3", lambda: 3 + 3),
        ]
        
        summary = executor.execute_sync(tasks)
        
        assert summary.total_tasks == 3
        assert summary.success_count == 3
        assert summary.fail_count == 0
    
    def test_execute_sync_with_failure(self):
        """동기 실행 일부 실패"""
        executor = ParallelExecutor(max_workers=2)
        
        def failing_task():
            raise ValueError("Test error")
        
        tasks = [
            ("task1", lambda: 1 + 1),
            ("task2", failing_task),
        ]
        
        summary = executor.execute_sync(tasks)
        
        assert summary.total_tasks == 2
        assert summary.success_count == 1
        assert summary.fail_count == 1
    
    def test_execute_sync_parallel_speedup(self):
        """동기 병렬 실행 속도 향상 확인"""
        executor = ParallelExecutor(max_workers=4)
        
        def slow_task(n):
            time.sleep(0.1)
            return n * 2
        
        tasks = [
            (f"task{i}", lambda n=i: slow_task(n))
            for i in range(4)
        ]
        
        start = time.time()
        summary = executor.execute_sync(tasks)
        elapsed = time.time() - start
        
        # 4개 작업을 0.1초씩 순차 실행하면 0.4초
        # 병렬 실행하면 ~0.1초 + 오버헤드
        assert elapsed < 0.3  # 병렬 실행이면 0.3초 미만
        assert summary.success_count == 4
    
    def test_execute_async_success(self):
        """비동기 실행 성공"""
        executor = ParallelExecutor(max_workers=2)
        
        async def async_task(n):
            await asyncio.sleep(0.01)
            return n * 2
        
        async def run_test():
            tasks = [
                ("task1", async_task(1)),
                ("task2", async_task(2)),
                ("task3", async_task(3)),
            ]
            return await executor.execute_async(tasks)
        
        summary = asyncio.run(run_test())
        
        assert summary.total_tasks == 3
        assert summary.success_count == 3
    
    def test_execute_async_with_failure(self):
        """비동기 실행 일부 실패"""
        executor = ParallelExecutor(max_workers=2)
        
        async def failing_task():
            raise ValueError("Async error")
        
        async def success_task():
            return "ok"
        
        async def run_test():
            tasks = [
                ("task1", success_task()),
                ("task2", failing_task()),
            ]
            return await executor.execute_async(tasks)
        
        summary = asyncio.run(run_test())
        
        assert summary.total_tasks == 2
        assert summary.success_count == 1
        assert summary.fail_count == 1


class TestToolsParallel:
    """Tool 병렬 실행 테스트"""
    
    def test_run_tools_parallel(self):
        """Tool 병렬 실행"""
        class MockTool:
            def invoke(self, args):
                return args.get("value", 0) * 2
        
        tool = MockTool()
        
        tool_calls = [
            ("tool1", tool, {"value": 1}),
            ("tool2", tool, {"value": 2}),
            ("tool3", tool, {"value": 3}),
        ]
        
        results = run_tools_parallel(tool_calls, max_workers=2)
        
        assert results["tool1"] == 2
        assert results["tool2"] == 4
        assert results["tool3"] == 6
